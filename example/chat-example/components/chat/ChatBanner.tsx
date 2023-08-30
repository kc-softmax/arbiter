"use client";

import { requestUserInfo } from "@/api/auth";
import { useChat } from "@/hooks/useChat";
import { useState } from "react";

const ChatBanner = () => {
  const {
    data: { roomId, users, notice },
  } = useChat();
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
      <div className="mockup-browser border border-base-300">
        <div className="mockup-browser-toolbar">
          <div className="bg-base-200 rounded-md flex-1 p-1">
            RoomID: {roomId}
          </div>
        </div>
      </div>

      {notice ? <div className="alert">[Notice] {notice}</div> : null}
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
    </div>
  );
};

export default ChatBanner;
