"use client";

import { useLogin } from "@/hooks/useLogin";
import { authAtom } from "@/store/authAtom";
import { useSetAtom } from "jotai";
import { useState } from "react";

interface StartChatPanelProps {
  next: () => void;
}

const StartChatPanel = ({ next }: StartChatPanelProps) => {
  const setAuthInfo = useSetAtom(authAtom);
  const [isSignUp, setIsSignUp] = useState(false);

  const { onSubmit, statusMessage, formControls } = useLogin({
    dev: {
      id: "@admin.com",
      password: "password",
    },
    onSuccess: ({ id, token }) => {
      setAuthInfo({ id, token });
      next();
    },
    onError: (error) => {
      alert(error.message);
    },
    config: {
      isSignUp,
    },
  });

  return (
    <section>
      <div>
        <form
          className="flex h-screen justify-center items-center"
          onSubmit={onSubmit}
        >
          <div className="border p-4 flex flex-col gap-4 rounded-md">
            <div className="tabs tabs-boxed">
              <a
                className={`tab basis-1/2 ${isSignUp ? "" : "tab-active"}`}
                onClick={() => setIsSignUp(false)}
              >
                Login
              </a>
              <a
                className={`tab basis-1/2 ${isSignUp ? "tab-active" : ""}`}
                onClick={() => setIsSignUp(true)}
              >
                Sign In
              </a>
            </div>
            <div className="join join-vertical">
              <input
                type="text"
                className="input input-bordered input-lg join-item"
                placeholder="Type Your Name"
                {...formControls.id}
              />
              <input
                type="password"
                className="input input-bordered input-lg join-item"
                placeholder="Type Your password"
                {...formControls.password}
              />
            </div>
            <button type="submit" className="btn btn-primary btn-lg w-auto">
              {statusMessage || "Start Chat"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
};

export default StartChatPanel;
