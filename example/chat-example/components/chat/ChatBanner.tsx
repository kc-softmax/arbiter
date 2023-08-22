"use client";

import { UserInfo } from "@/@types/chat";
import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";
import { useState } from "react";

export interface ChatBannerProps {
  roomId: string;
  users: UserInfo[];
}

const ChatBanner = ({ roomId, users }: ChatBannerProps) => {
  const { token } = useAtomValue(authAtom);
  const [tooltip, setTooltip] = useState<Record<string, string>>({});

  const requestUserInfo = async (id: string) => {
    if (tooltip[id]) return;

    // TODO: 유저 정보 요청으로 바꿀 예정
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_HOST}/auth/console/console-user`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          authorization: `Bearer ${token}`,
        },
        // TODO: 진짜 유저 id로 바꿀 예정
        body: JSON.stringify({ id }),
      }
    );

    const result = await response.json();

    setTooltip((prev) => ({
      ...prev,
      [id]: `${result.email}
        Last Login: ${result.updated_at}`,
    }));
  };

  return (
    <div className="text-center sticky top-0 z-10">
      <p className="font-semibold">RoomID: {roomId}</p>
      <div>
        {users.map(({ id, name }) => (
          <p
            key={id}
            className="tooltip tooltip-bottom"
            data-tip={tooltip[name]}
          >
            <span className="badge" onMouseOver={() => requestUserInfo(id)}>
              {name}
            </span>
          </p>
        ))}
      </div>
    </div>
  );
};

export default ChatBanner;
