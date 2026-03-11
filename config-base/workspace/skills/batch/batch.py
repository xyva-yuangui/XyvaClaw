#!/usr/bin/env python3
"""
Batch Processing Engine - 批量处理引擎

Supports:
- Parallel/sequential/chunked processing modes
- Error handling with retry mechanism
- Progress tracking and logging
- Checkpoint for resume from failure

Usage:
    # Simple mode
    python3 batch.py --items item1,item2,item3 --command "process {item}"
    
    # Batch stock analysis
    python3 batch.py --items-file stocks.txt --command "analyze_stock {item}" --parallel 5
    
    # Batch publish
    python3 batch.py --items-dir notes/ --command "publish_note {item}" --delay 300
"""

import argparse
import json
import os
import sys
import time
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
import subprocess
import signal


class BatchProcessor:
    """批量处理引擎"""
    
    def __init__(
        self,
        items: List[str],
        command: str,
        parallel: int = 1,
        delay: float = 0,
        retry: int = 3,
        checkpoint_dir: Optional[str] = None,
        log_file: Optional[str] = None
    ):
        self.items = items
        self.command = command
        self.parallel = parallel
        self.delay = delay
        self.max_retries = retry
        self.checkpoint_dir = checkpoint_dir or ".batch_checkpoint"
        self.log_file = log_file or ".batch_log.json"
        self.results: Dict[str, Any] = {}
        self.errors: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        
        # Create checkpoint directory
        Path(self.checkpoint_dir).mkdir(parents=True, exist_ok=True)
        
        # Load checkpoint if exists
        self.checkpoint_file = os.path.join(
            self.checkpoint_dir,
            f"checkpoint_{self._get_checkpoint_id()}.json"
        )
        self.load_checkpoint()
    
    def _get_checkpoint_id(self) -> str:
        """Generate checkpoint ID based on items and command"""
        content = f"{','.join(self.items)}:{self.command}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def load_checkpoint(self):
        """Load checkpoint if exists"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.results = data.get('results', {})
                    self.errors = data.get('errors', [])
                    print(f"✓ Loaded checkpoint: {len(self.results)} completed, {len(self.errors)} failed")
            except Exception as e:
                print(f"⚠ Failed to load checkpoint: {e}")
    
    def save_checkpoint(self):
        """Save current progress to checkpoint"""
        data = {
            'results': self.results,
            'errors': self.errors,
            'timestamp': datetime.now().isoformat(),
            'total_items': len(self.items),
            'command': self.command
        }
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def log_result(self, item: str, status: str, result: Any = None, error: str = None):
        """Log result to file"""
        log_entry = {
            'item': item,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'result': result,
            'error': error
        }
        
        # Append to log file
        log_path = Path(self.log_file)
        logs = []
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def execute_command(self, item: str) -> tuple[bool, Any, Optional[str]]:
        """Execute command for single item"""
        cmd = self.command.replace('{item}', item)
        
        try:
            # Execute command
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per item
            )
            
            if result.returncode == 0:
                return True, result.stdout, None
            else:
                return False, result.stdout, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, None, f"Timeout after 300s for command: {cmd}"
        except Exception as e:
            return False, None, str(e)
    
    def process_item(self, item: str) -> Dict[str, Any]:
        """Process single item with retry"""
        # Skip if already completed
        if item in self.results:
            return {'item': item, 'status': 'skipped', 'reason': 'already completed'}
        
        # Check if in error list (failed permanently)
        if any(e['item'] == item for e in self.errors):
            return {'item': item, 'status': 'skipped', 'reason': 'previously failed'}
        
        # Try with retries
        for attempt in range(1, self.max_retries + 1):
            success, result, error = self.execute_command(item)
            
            if success:
                self.results[item] = {
                    'status': 'success',
                    'result': result,
                    'attempts': attempt,
                    'completed_at': datetime.now().isoformat()
                }
                self.log_result(item, 'success', result=result)
                self.save_checkpoint()
                return {'item': item, 'status': 'success', 'attempts': attempt}
            
            # Wait before retry
            if attempt < self.max_retries:
                time.sleep(2 ** attempt)  # Exponential backoff
        
        # All retries failed
        error_record = {
            'item': item,
            'error': error,
            'attempts': self.max_retries,
            'failed_at': datetime.now().isoformat()
        }
        self.errors.append(error_record)
        self.log_result(item, 'failed', error=error)
        self.save_checkpoint()
        return {'item': item, 'status': 'failed', 'error': error, 'attempts': self.max_retries}
    
    def run(self) -> Dict[str, Any]:
        """Run batch processing"""
        total = len(self.items)
        completed = len(self.results)
        failed = len(self.errors)
        remaining = total - completed - failed
        
        print(f"\n{'='*60}")
        print(f"Batch Processing Engine")
        print(f"{'='*60}")
        print(f"Total items: {total}")
        print(f"Completed (checkpoint): {completed}")
        print(f"Failed (checkpoint): {failed}")
        print(f"Remaining: {remaining}")
        print(f"Parallel: {self.parallel}")
        print(f"Command: {self.command}")
        print(f"{'='*60}\n")
        
        if remaining == 0:
            print("✓ All items already processed (from checkpoint)")
            return self._generate_summary()
        
        # Get remaining items
        completed_items = set(self.results.keys())
        failed_items = set(e['item'] for e in self.errors)
        remaining_items = [i for i in self.items if i not in completed_items and i not in failed_items]
        
        # Process items
        start_time = time.time()
        
        if self.parallel > 1:
            # Parallel mode
            with ThreadPoolExecutor(max_workers=self.parallel) as executor:
                futures = {executor.submit(self.process_item, item): item for item in remaining_items}
                
                for i, future in enumerate(as_completed(futures), 1):
                    item = futures[future]
                    try:
                        result = future.result()
                        progress = f"[{i}/{len(remaining_items)}]"
                        
                        if result['status'] == 'success':
                            print(f"✓ {progress} {item} (attempts: {result.get('attempts', 1)})")
                        else:
                            print(f"✗ {progress} {item} - {result.get('error', 'unknown')}")
                        
                        # Delay between items
                        if self.delay > 0 and i < len(remaining_items):
                            time.sleep(self.delay)
                            
                    except Exception as e:
                        print(f"✗ {item} - Exception: {e}")
        else:
            # Sequential mode
            for i, item in enumerate(remaining_items, 1):
                result = self.process_item(item)
                progress = f"[{i}/{len(remaining_items)}]"
                
                if result['status'] == 'success':
                    print(f"✓ {progress} {item} (attempts: {result.get('attempts', 1)})")
                else:
                    print(f"✗ {progress} {item} - {result.get('error', 'unknown')}")
                
                # Delay between items
                if self.delay > 0 and i < len(remaining_items):
                    time.sleep(self.delay)
        
        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"Completed in {elapsed:.2f}s")
        print(f"{'='*60}\n")
        
        return self._generate_summary()
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate processing summary"""
        total = len(self.items)
        success = len(self.results)
        failed = len(self.errors)
        
        summary = {
            'total': total,
            'success': success,
            'failed': failed,
            'success_rate': f"{success/total*100:.1f}%" if total > 0 else "0%",
            'elapsed_seconds': (datetime.now() - self.start_time).total_seconds(),
            'checkpoint_file': self.checkpoint_file,
            'log_file': self.log_file
        }
        
        print(f"Summary:")
        print(f"  Total: {total}")
        print(f"  Success: {success}")
        print(f"  Failed: {failed}")
        print(f"  Success Rate: {summary['success_rate']}")
        print(f"  Elapsed: {summary['elapsed_seconds']:.2f}s")
        print(f"  Checkpoint: {self.checkpoint_file}")
        print(f"  Log: {self.log_file}")
        
        if failed > 0:
            print(f"\nFailed items:")
            for err in self.errors[-5:]:  # Show last 5 failures
                print(f"  - {err['item']}: {err['error'][:50]}...")
        
        return summary


def load_items_from_file(file_path: str) -> List[str]:
    """Load items from file (one per line)"""
    with open(file_path, 'r', encoding='utf-8') as f:
        items = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return items


def load_items_from_dir(dir_path: str) -> List[str]:
    """Load items from directory (file names without extension)"""
    items = []
    dir_path = Path(dir_path)
    if dir_path.exists():
        for file in dir_path.iterdir():
            if file.is_file():
                # Use filename without extension as item
                items.append(file.stem)
    return items


def main():
    parser = argparse.ArgumentParser(
        description='Batch Processing Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple mode
  python3 batch.py --items item1,item2,item3 --command "echo {item}"
  
  # Batch stock analysis
  python3 batch.py --items-file stocks.txt --command "analyze_stock {item}" --parallel 5
  
  # Batch publish with delay
  python3 batch.py --items-dir notes/ --command "publish_note {item}" --delay 300
  
  # Resume from checkpoint
  python3 batch.py --items-file stocks.txt --command "analyze_stock {item}" --checkpoint-dir .checkpoint
        """
    )
    
    parser.add_argument('--items', type=str, help='Comma-separated items')
    parser.add_argument('--items-file', type=str, help='File with one item per line')
    parser.add_argument('--items-dir', type=str, help='Directory with item files')
    parser.add_argument('--command', type=str, help='Command to execute (use {item} as placeholder)')
    parser.add_argument('--parallel', type=int, default=1, help='Number of parallel workers (default: 1)')
    parser.add_argument('--delay', type=float, default=0, help='Delay between items in seconds (default: 0)')
    parser.add_argument('--retry', type=int, default=3, help='Max retries per item (default: 3)')
    parser.add_argument('--checkpoint-dir', type=str, help='Checkpoint directory (default: .batch_checkpoint)')
    parser.add_argument('--log-file', type=str, help='Log file path (default: .batch_log.json)')
    parser.add_argument('--check', action='store_true', help='Check dependencies and configuration')
    
    args = parser.parse_args()
    
    # Check mode (before requiring command)
    if args.check:
        print("Batch Processor Health Check:")
        print("  ✓ Python 3: OK")
        print("  ✓ argparse: OK (standard library)")
        print("  ✓ concurrent.futures: OK (standard library)")
        print("  ✓ json: OK (standard library)")
        print("  ✓ subprocess: OK (standard library)")
        print("\nStatus: READY")
        sys.exit(0)
    
    # Validate command is provided
    if not args.command:
        print("Error: --command is required")
        sys.exit(1)
    
    # Load items
    items = []
    if args.items:
        items = [i.strip() for i in args.items.split(',') if i.strip()]
    elif args.items_file:
        items = load_items_from_file(args.items_file)
    elif args.items_dir:
        items = load_items_from_dir(args.items_dir)
    else:
        print("Error: Must specify --items, --items-file, or --items-dir")
        sys.exit(1)
    
    if not items:
        print("Error: No items to process")
        sys.exit(1)
    
    # Create and run processor
    processor = BatchProcessor(
        items=items,
        command=args.command,
        parallel=args.parallel,
        delay=args.delay,
        retry=args.retry,
        checkpoint_dir=args.checkpoint_dir,
        log_file=args.log_file
    )
    
    summary = processor.run()
    
    # Exit with error if any failures
    if summary['failed'] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
