"use client";

import { Provider } from "jotai";
import React, { PropsWithChildren } from "react";

const Providers = ({ children }: PropsWithChildren) => {
  return <Provider>{children}</Provider>;
};

export default Providers;
