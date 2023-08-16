import { pretendardFont } from "@/style/localFonts";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Arbiter Chat Application Example",
  description: "Arbiter Chat Application Example",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className={`${pretendardFont.variable}`}>{children}</body>
    </html>
  );
}
