import React from 'react';

export default function StepIndicator({ steps, current }) {
  return (
    <div className="flex items-center justify-center gap-1">
      {steps.map((step, i) => (
        <React.Fragment key={step.id}>
          <div className="flex flex-col items-center">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center text-lg transition-all ${
                i < current
                  ? 'bg-brand-600 text-white'
                  : i === current
                  ? 'bg-brand-100 text-brand-700 ring-2 ring-brand-400'
                  : 'bg-gray-100 text-gray-400'
              }`}
            >
              {i < current ? '✓' : step.icon}
            </div>
            <span
              className={`text-xs mt-1 ${
                i === current ? 'text-brand-700 font-medium' : 'text-gray-400'
              }`}
            >
              {step.label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div
              className={`w-8 h-0.5 mb-5 ${
                i < current ? 'bg-brand-400' : 'bg-gray-200'
              }`}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}
