import { useAuth0 } from "@auth0/auth0-react";

export default function AuthPanel() {
  const {
    isLoading,
    isAuthenticated,
    error,
    loginWithRedirect,
    logout,
    user,
  } = useAuth0();

  const logoutUri =
    import.meta.env.VITE_AUTH0_LOGOUT_URI || "http://localhost:5173/";

  const signup = () => {
    loginWithRedirect({
      authorizationParams: {
        screen_hint: "signup",
      },
    });
  };

  const login = () => {
    loginWithRedirect();
  };

  const handleLogout = () => {
    logout({
      logoutParams: {
        returnTo: logoutUri,
      },
    });
  };

  if (isLoading) {
    return (
      <section className="auth-panel">
        <strong>Apex Login:</strong> Loading authentication...
      </section>
    );
  }

  if (error) {
    return (
      <section className="auth-panel auth-panel-error">
        <strong>Auth0 Error:</strong> {error.message}
      </section>
    );
  }

  if (!isAuthenticated) {
    return (
      <section className="auth-panel">
        <strong>Apex Operations Login</strong>

        <div className="auth-panel-actions">
          <button type="button" onClick={login}>
            Login
          </button>

          <button type="button" onClick={signup}>
            Signup
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="auth-panel">
      <strong>Logged in:</strong> {user?.email || user?.name || "Unknown user"}

      <div className="auth-panel-actions">
        <button type="button" onClick={handleLogout}>
          Logout
        </button>
      </div>
    </section>
  );
}
