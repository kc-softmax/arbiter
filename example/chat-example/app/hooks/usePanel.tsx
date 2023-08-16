"use client";

import { useState } from "react";

interface PanelStepProps<T extends readonly string[]> {
  children: React.ReactNode;
  name: T[number];
}

export const usePanel = <T extends readonly string[]>(steps: T) => {
  const [activeStep, setActiveStep] = useState<T[number]>(steps[0]);

  const PanelStep = ({ children, name }: PanelStepProps<T>) => {
    if (activeStep !== name) return null;

    return <>{children}</>;
  };

  return {
    PanelStep,
    activeStep,
    setActiveStep,
  };
};
