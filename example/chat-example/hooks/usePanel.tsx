"use client";

import { cloneElement, useState } from "react";

interface PanelStepProps<T extends readonly string[]> {
  children: React.ReactNode;
  name: T[number];
  next?: () => void;
}

export const usePanel = <T extends readonly string[]>(steps: T) => {
  const [activeStep, setActiveStep] = useState<T[number]>(steps[0]);

  const PanelStep = ({ children, name, next }: PanelStepProps<T>) => {
    if (activeStep !== name) return null;

    const newChildren = cloneElement(children as React.ReactElement, {
      next,
    });

    return <>{newChildren}</>;
  };

  return {
    PanelStep,
    activeStep,
    setActiveStep,
  };
};
