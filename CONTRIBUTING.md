# Contributing to xyvaClaw

感谢你对 xyvaClaw 的关注！欢迎任何形式的贡献。

Thank you for your interest in xyvaClaw! All contributions are welcome.

## How to Contribute

### Report Bugs / 提交 Bug

1. Check [existing issues](https://github.com/xyva-yuangui/XyvaClaw/issues) first
2. Open a new issue with:
   - OS and version (e.g. macOS 14.3)
   - Steps to reproduce
   - Expected vs actual behavior
   - Logs (if any): `~/.xyvaclaw/logs/`

### Feature Requests / 功能建议

Open an issue with the `enhancement` label. Describe the use case and expected behavior.

### Submit Code / 提交代码

```bash
# 1. Fork this repo
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/XyvaClaw.git
cd XyvaClaw

# 3. Create a branch
git checkout -b feature/your-feature

# 4. Make changes
# 5. Test locally
bash xyvaclaw-setup.sh

# 6. Commit
git add -A
git commit -m "feat: description of your change"

# 7. Push and open PR
git push origin feature/your-feature
```

### Add a New Skill / 添加新技能

1. Create `config-base/workspace/skills/your-skill/SKILL.md`
2. Add `scripts/check.py` for dependency checking
3. Add your main script(s) in `scripts/`
4. Test with `python3 scripts/check.py`

See existing skills for examples.

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation only
- `perf:` — performance improvement
- `refactor:` — code refactoring
- `style:` — formatting, no code change
- `test:` — adding tests
- `chore:` — maintenance

## Code Style

- **Shell scripts**: Follow existing `xyvaclaw-setup.sh` style
- **Python**: PEP 8, type hints preferred
- **JavaScript/TypeScript**: Follow existing extension style
- **SKILL.md**: Use YAML frontmatter + Markdown body

## Questions?

- 💬 QQ 群: 1087471835
- 💬 Discord: https://discord.gg/QABg4Z2Mzu
- 📧 Open an issue
