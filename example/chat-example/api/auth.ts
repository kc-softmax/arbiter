interface RequestSignUpParams {
  id: string;
  password: string;
}

export const requestSignUp = async ({ id, password }: RequestSignUpParams) => {
  const body = {
    email: id,
    password,
  };

  const response = await fetch(
    `${process.env.NEXT_PUBLIC_HOST}/auth/game/signup/email`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    }
  );

  if (!response.ok) throw new Error("Sign Up Failed");

  const data = await response.json();

  return data;
};

interface UpdateUserInfoParams {
  id: string;
  token: string;
}

export const updateUserInfo = async ({ id, token }: UpdateUserInfoParams) => {
  const body = {
    user_name: id.split("@")[0],
  };

  const response = await fetch(`${process.env.NEXT_PUBLIC_HOST}/auth/game/me`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) throw new Error("Update User Info Failed");

  const data = await response.json();

  return data;
};

interface RequestLoginParams {
  id: string;
  password: string;
}

export const requestLogin = async ({ id, password }: RequestLoginParams) => {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_HOST}/auth/game/login/email`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: `username=${id}&password=${password}`,
    }
  );

  if (!response.ok) throw new Error("Login Failed");

  const data: { access_token: string; refresh_token: string } =
    await response.json();

  return data;
};

export const requestUserInfo = async (id: string) => {
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

  return result;
};
