import { fetchHeadText } from "@/utils/fetchLinkPreview";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

interface ChatLinkPreviewProps {
  messageText: string;
}

const ChatLinkPreview = ({ messageText }: ChatLinkPreviewProps) => {
  const [targetUrl, setTargetUrl] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState({
    title: "",
    description: "",
    image: "",
  });

  useEffect(() => {
    const urlRegex = new RegExp(`(https?://[^\\s]+)`);
    const urlMatch = messageText.match(urlRegex);

    if (!urlMatch) return;

    const fetchLinkPreview = async () => {
      const headText = await fetchHeadText(urlMatch[1]);

      if (!headText) return;

      const parser = new DOMParser();
      const doc = parser.parseFromString(headText, "text/html");

      const title = doc.querySelector("title")?.textContent ?? "";
      const description =
        doc.querySelector("meta[name=description]")?.getAttribute("content") ??
        "";
      const image =
        doc
          .querySelector("meta[property='og:image']")
          ?.getAttribute("content") ?? "";

      setPreviewData({ title, description, image });
      setTargetUrl(urlMatch[1]);
    };

    fetchLinkPreview();
  }, [messageText]);

  const { title, description, image } = previewData;

  if (!targetUrl) return null;

  return (
    <div className="row-start-4 max-w-lg">
      <Link href={targetUrl} rel="noopener noreferrer" target="_blank">
        <div className="card card-compact bg-base-100 border hover:brightness-90 cursor-pointer">
          <figure className="relative aspect-video">
            <Image
              src={image}
              alt={title}
              unoptimized
              fill
              className="object-cover"
            />
          </figure>
          <div className="card-body">
            <h2 className="card-title">{title}</h2>
            <p className="text-ellipsis">{description}</p>
          </div>
        </div>
      </Link>
    </div>
  );
};

export default ChatLinkPreview;
