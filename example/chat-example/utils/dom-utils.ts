import { RefObject } from "react";

export const scrollToBottom = (ref: RefObject<HTMLDivElement>) => {
  ref.current?.scrollTo({
    top: ref.current.scrollHeight,
    behavior: "smooth",
  });
};
