"use client";

import { UserInfo } from "@/@types/chat";
import { useState } from "react";

export interface ChatBannerProps {
  roomId: string;
  users: UserInfo[];
}

const ChatBanner = ({ roomId, users }: ChatBannerProps) => {
  const [tooltip, setTooltip] = useState<Record<string, string>>({});

  const requestUserInfo = async (id: string) => {
    if (tooltip[id]) return;

    const response = await fetch(
      `${process.env.NEXT_PUBLIC_HOST}/auth/game/user`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ id }),
      }
    );

    const result = await response.json();

    setTooltip((prev) => ({
      ...prev,
      [id]: `${result.email} /
        Last Login: ${new Date(result.updated_at).toLocaleString()}`,
    }));
  };

  return (
    <div className="text-center sticky top-0 z-10">
      <p className="font-semibold">RoomID: {roomId}</p>
      <div>
        {users.map(({ user_id, user_name }, index) => (
          <p
            key={`${user_id}-${user_name}(${index})`}
            className="tooltip tooltip-bottom"
            data-tip={tooltip[user_id]}
          >
            <span
              className="badge"
              onMouseOver={() => requestUserInfo(user_id.toString())}
            >
              {user_name || "Unknown"}
            </span>
          </p>
        ))}
      </div>
    </div>
  );
};

export default ChatBanner;
