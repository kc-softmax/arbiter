"use client";

import { UserInfo } from "@/@types/chat";
import { requestUserInfo } from "@/api/auth";
import { useState } from "react";

export interface ChatBannerProps {
  roomId: string;
  users: UserInfo[];
}

const ChatBanner = ({ roomId, users }: ChatBannerProps) => {
  const [tooltip, setTooltip] = useState<Record<string, string>>({});

  const getUserInfo = async (userId: string) => {
    if (tooltip[userId]) return;

    const data = await requestUserInfo(userId);

    setTooltip((prev) => ({
      ...prev,
      [userId]: `${data.email} /
        Last Login: ${new Date(data.updated_at).toLocaleString()}`,
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
              onMouseOver={() => getUserInfo(user_id.toString())}
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
