"use client";

import { UserInfo } from "@/@types/chat";
import { requestUserInfo } from "@/api/auth";
import { useState } from "react";

export interface ChatBannerProps {
  roomId: string;
  users: UserInfo[];
  notice: string | null;
}

const ChatBanner = ({ roomId, users, notice }: ChatBannerProps) => {
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
    <div className="text-center sticky top-0 z-10 space-y-2">
      <p className="font-semibold">RoomID: {roomId}</p>
      <ul>
        {users.map(({ user_id, user_name }, index) => (
          <li
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
          </li>
        ))}
      </ul>
      {notice ? <div className="alert">Notice: {notice}</div> : null}
    </div>
  );
};

export default ChatBanner;
