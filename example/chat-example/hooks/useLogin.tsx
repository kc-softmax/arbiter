import { AuthInfo } from "@/@types/chat";
import { requestLogin, requestSignUp, updateUserInfo } from "@/api/auth";
import { ChangeEvent, useState } from "react";

const isDev = process.env.NODE_ENV === "development";

interface UseLoginParams {
  dev?: {
    id?: string;
    password?: string;
  };
  config?: {
    isSignUp?: boolean;
  };
  onSuccess?: (data: AuthInfo) => void;
  onError?: (error: Error) => void;
}

export const useLogin = ({
  dev,
  onError,
  onSuccess,
  config: { isSignUp } = {
    isSignUp: false,
  },
}: UseLoginParams) => {
  const [id, setID] = useState(isDev && dev ? dev.id : "");
  const [password, setPassword] = useState(isDev && dev ? dev.password : "");
  const [statusMessage, setStatusMessage] = useState("");

  const getIdFromToken = (token: string) => {
    const payload = token.split(".")[1];
    const { sub } = JSON.parse(atob(payload)) as {
      sub: string;
    };

    return sub;
  };

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!id || !password) return alert("Please enter your ID and password");

    try {
      if (isSignUp) {
        setStatusMessage("Signing Up...");
        await requestSignUp({ id, password });
      }

      setStatusMessage("Logging In...");
      const tokens = await requestLogin({ id, password });

      const { access_token } = tokens;

      const idFromToken = getIdFromToken(access_token);

      setStatusMessage("Updating User Info...");
      await updateUserInfo({
        id,
        token: access_token,
      });

      setStatusMessage("Done!");

      onSuccess?.({
        id: idFromToken,
        token: access_token,
      });
    } catch (error) {
      setStatusMessage("");
      if (error instanceof Error) {
        onError?.(error);
      }
    }
  };

  return {
    onSubmit,
    statusMessage,
    formControls: {
      id: {
        onChange(e: ChangeEvent<HTMLInputElement>) {
          setID(e.target.value);
        },
        value: id,
      },
      password: {
        onChange(e: ChangeEvent<HTMLInputElement>) {
          setPassword(e.target.value);
        },
        value: password,
      },
    },
  };
};
