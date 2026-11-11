import {
    ChevronDown,
    User,
    Settings,
    LogOut,
} from "lucide-react";

import {
    useEffect,
    useRef,
    useState,
} from "react";

import {
    useNavigate,
} from "react-router-dom";

import api, {
    clearToken,
} from "../services/api";

interface CurrentUser {
    id: string;
    email: string;
    full_name: string | null;
    plan_id: string;
    is_active: boolean;
    is_verified: boolean;
}

export default function Topbar() {
    const navigate = useNavigate();

    const [user, setUser] =
        useState<CurrentUser | null>(null);

    const [open, setOpen] =
        useState(false);

    const menuRef =
        useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        let mounted = true;

        async function loadUser() {
            try {
                const response =
                    await api.get<CurrentUser>(
                        "/api/auth/me",
                    );

                if (mounted) {
                    setUser(response.data);
                }
            } catch {
                if (mounted) {
                    setUser(null);
                }
            }
        }

        loadUser();

        return () => {
            mounted = false;
        };
    }, []);

    useEffect(() => {
        function handleClickOutside(
            event: MouseEvent,
        ) {
            if (
                menuRef.current &&
                !menuRef.current.contains(
                    event.target as Node,
                )
            ) {
                setOpen(false);
            }
        }

        document.addEventListener(
            "mousedown",
            handleClickOutside,
        );

        return () => {
            document.removeEventListener(
                "mousedown",
                handleClickOutside,
            );
        };
    }, []);

    function getDisplayName() {
        if (user?.full_name?.trim()) {
            return user.full_name;
        }

        if (user?.email) {
            return user.email.split("@")[0];
        }

        return "Account";
    }

    function getInitials() {
        const name = getDisplayName();

        const parts = name
            .trim()
            .split(/\s+/)
            .filter(Boolean);

        if (parts.length >= 2) {
            return (
                parts[0][0] +
                parts[parts.length - 1][0]
            ).toUpperCase();
        }

        return name
            .slice(0, 2)
            .toUpperCase();
    }

    function handleLogout() {
        clearToken();

        localStorage.removeItem("token");
        localStorage.removeItem(
            "pending_payment_id",
        );
        localStorage.removeItem(
            "pending_payment_reference",
        );

        navigate("/login", {
            replace: true,
        });
    }

    return (
        <header className="topbar">
            <div className="topbar-left">
                <div className="topbar-title">
                    CloudBox
                </div>
            </div>

            <div
                className="topbar-account"
                ref={menuRef}
            >
                <button
                    type="button"
                    className="account-button"
                    onClick={() =>
                        setOpen(
                            (current) => !current,
                        )
                    }
                >
                    <div className="account-avatar">
                        {getInitials()}
                    </div>

                    <div className="account-details">
                        <strong>
                            {getDisplayName()}
                        </strong>

                        <span>
                            {user?.email ||
                                "Loading..."}
                        </span>
                    </div>

                    <ChevronDown
                        size={17}
                    />
                </button>

                {open && (
                    <div className="account-menu">
                        <button
                            type="button"
                            onClick={() => {
                                setOpen(false);
                                navigate(
                                    "/profile",
                                );
                            }}
                        >
                            <User size={17} />
                            Profile
                        </button>

                        <button
                            type="button"
                            onClick={() => {
                                setOpen(false);
                                navigate(
                                    "/settings",
                                );
                            }}
                        >
                            <Settings size={17} />
                            Settings
                        </button>

                        <div className="account-menu-divider" />

                        <button
                            type="button"
                            className="logout-item"
                            onClick={
                                handleLogout
                            }
                        >
                            <LogOut size={17} />
                            Log out
                        </button>
                    </div>
                )}
            </div>
        </header>
    );
}