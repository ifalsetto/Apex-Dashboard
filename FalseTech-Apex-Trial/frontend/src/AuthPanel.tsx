import { useAuth0 } from "@auth0/auth0-react";

function localAppUrl(value?: string): string {
  return value?.trim() || `${window.location.origin}/`;
}

function auth0Configured(): boolean {
  return Boolean(
    import.meta.env.VITE_AUTH0_DOMAIN?.trim() &&
      import.meta.env.VITE_AUTH0_CLIENT_ID?.trim(),
  );
}

function AuthPanelDisabled() {
  return (
    <section className="auth-panel auth-panel-muted">
      <strong>FalseTech Apex Dashboard v2 Beta:</strong> Local mode. Auth0 is not configured for this browser session.
    </section>
  );
}

function AuthPanelConnected() {
  const {
    isLoading,
    isAuthenticated,
    error,
    loginWithRedirect,
    logout,
    user,
  } = useAuth0();

  const redirectUri = localAppUrl(import.meta.env.VITE_AUTH0_REDIRECT_URI);
  const logoutUri = localAppUrl(
    import.meta.env.VITE_AUTH0_LOGOUT_URI || import.meta.env.VITE_AUTH0_REDIRECT_URI,
  );

  const signup = () => {
    void loginWithRedirect({
      authorizationParams: {
        redirect_uri: redirectUri,
        screen_hint: "signup",
      },
    });
  };

  const login = () => {
    void loginWithRedirect({
      authorizationParams: {
        redirect_uri: redirectUri,
      },
    });
  };

  const handleLogout = () => {
    void logout({
      logoutParams: {
        returnTo: logoutUri,
      },
    });
  };

  if (isLoading) {
    return (
      <section className="auth-panel">
        <strong>Apex Dashboard Login:</strong> Loading authentication...
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
        <strong>Apex Dashboard Login</strong>

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

export default function AuthPanel() {
  if (!auth0Configured()) {
    return <AuthPanelDisabled />;
  }

  return <AuthPanelConnected />;
}
