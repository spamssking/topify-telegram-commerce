import {
    useEffect,
    useState,
} from "react";

import {
    Navigate,
    Outlet,
    useLocation,
} from "react-router-dom";

import api, {
    getToken,
} from "../services/api";

function ProtectedRoute() {
    const location = useLocation();

    const [checking, setChecking] =
        useState(true);

    const [authenticated, setAuthenticated] =
        useState(false);

    useEffect(() => {
        let mounted = true;

        async function checkAuthentication() {
            const token = getToken();

            if (!token) {
                if (mounted) {
                    setAuthenticated(false);
                    setChecking(false);
                }

                return;
            }

            try {
                await api.get("/api/auth/me");

                if (mounted) {
                    setAuthenticated(true);
                }
            } catch {
                if (mounted) {
                    setAuthenticated(false);
                }
            } finally {
                if (mounted) {
                    setChecking(false);
                }
            }
        }

        checkAuthentication();

        return () => {
            mounted = false;
        };
    }, []);

    if (checking) {
        return (
            <div className="dashboard-loading">
                Checking authentication...
            </div>
        );
    }

    if (!authenticated) {
        return (
            <Navigate
                to="/login"
                replace
                state={{
                    from: location.pathname,
                }}
            />
        );
    }

    return <Outlet />;
}

export default ProtectedRoute;
