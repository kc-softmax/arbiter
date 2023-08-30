export const sortTargetItemFirst = <T>(a: T, b: T, target: T) => {
  if (a === target) return -1;
  if (b === target) return 1;
  return 0;
};
