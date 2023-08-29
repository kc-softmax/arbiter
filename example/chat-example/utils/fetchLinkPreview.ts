"use server";

export const fetchHeadText = async (matchedUrl: string) => {
  const res = await fetch(matchedUrl, {});

  if (!res.ok) return;

  const htmlContent = await res.text();
  const head = htmlContent.match(/<head[^>]*>[\s\S]*<\/head>/gi);

  return head?.[0];
};
