import {
    CircleHelp,
    Crown,
    Home,
    Settings,
    HardDrive,
    Upload,
    X,
    LogOut,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import "./Sidebar.css";


type Plan = {
    code: string;
    name: string;
    storage_quota_bytes: number;
};

type NavItemProps = {
    to: string;
    icon: React.ReactNode;
    label: string;
    end?: boolean;
    onClick?: () => void;
};

function NavItem({
    to,
    icon,
    label,
    end,
    onClick,
}: NavItemProps) {
    return (
        <NavLink
            to={to}
            end={end}
            onClick={onClick}
            className={({ isActive }) =>
                `sidebar-nav-item ${isActive ? "active" : ""}`
            }
        >
            <span className="sidebar-nav-icon">
                {icon}
            </span>

            <span>{label}</span>
        </NavLink>
    );
}

/**
 * Convert bytes into a readable storage value.
 *
 * Examples:
 * 5368709120  -> 5 GB
 * 107374182400 -> 100 GB
 */
function formatStorage(bytes: number) {
    if (!bytes || bytes <= 0) {
        return "0 GB";
    }

    const gb = bytes / (1024 * 1024 * 1024);

    if (gb >= 1) {
        return `${Math.round(gb)} GB`;
    }

    const mb = bytes / (1024 * 1024);

    return `${Math.round(mb)} MB`;
}

export default function Sidebar() {
    const navigate = useNavigate();

    /*
     * Replace this temporary value with the actual authenticated
     * user's plan returned by your backend.
     *
     * Example backend response:
     *
     * {
     *     "code": "FREE",
     *     "name": "Free",
     *     "storage_quota_bytes": 5368709120
     * }
     *
     * or:
     *
     * {
     *     "code": "PRO",
     *     "name": "Pro",
     *     "storage_quota_bytes": 107374182400
     * }
     */
    const plan: Plan = {
        code: "FREE",
        name: "Free",
        storage_quota_bytes: 5368709120,
    };

    const isPaidPlan = plan.code !== "FREE";

    const planName = `${plan.name} plan`;

    const storage = formatStorage(
        plan.storage_quota_bytes
    );

    const closeMobileSidebar = () => {
        document.body.classList.remove("sidebar-open");
    };

    const handleUpgrade = () => {
        closeMobileSidebar();
        navigate("/upgrade");
    };

    const handleLogout = () => {
        closeMobileSidebar();

        localStorage.removeItem("access_token");
        localStorage.removeItem("token");

        navigate("/login", {
            replace: true,
        });
    };

    return (
        <>
            <aside className="app-sidebar">
                {/* =========================
                    BRAND
                   ========================= */}

                <div className="sidebar-brand">
                    <div className="sidebar-brand-icon">
                        <HardDrive
                            size={21}
                            strokeWidth={2.2}
                        />
                    </div>

                    <span>CloudBox</span>

                    <button
                        className="sidebar-close"
                        type="button"
                        onClick={closeMobileSidebar}
                        aria-label="Close navigation"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* =========================
                    HOME
                   ========================= */}

                <div className="sidebar-section">
                    <div className="sidebar-section-label">
                        Home
                    </div>

                    <nav className="sidebar-nav">
                        <NavItem
                            to="/dashboard"
                            label="Home"
                            end
                            icon={<Home size={19} />}
                            onClick={closeMobileSidebar}
                        />

                        <NavItem
                            to="/files"
                            label="Storage"
                            icon={<HardDrive size={19} />}
                            onClick={closeMobileSidebar}
                        />
                    </nav>
                </div>

                {/* =========================
                    SERVICES
                   ========================= */}

                <div className="sidebar-section">
                    <div className="sidebar-section-label">
                        Services
                    </div>

                    <nav className="sidebar-nav">
                        <NavItem
                            to="/upgrade"
                            label="Plans"
                            icon={<Crown size={19} />}
                            onClick={closeMobileSidebar}
                        />

                        <button
                            type="button"
                            className="sidebar-nav-item sidebar-button"
                            onClick={() => {
                                closeMobileSidebar();
                                navigate("/files");
                            }}
                        >
                            <span className="sidebar-nav-icon">
                                <Upload size={19} />
                            </span>

                            <span>Upload files</span>
                        </button>
                    </nav>
                </div>

                {/* =========================
                    ACCOUNT
                   ========================= */}

                <div className="sidebar-section">
                    <div className="sidebar-section-label">
                        Account
                    </div>

                    <nav className="sidebar-nav">
                        <NavItem
                            to="/settings"
                            label="Settings"
                            icon={<Settings size={19} />}
                            onClick={closeMobileSidebar}
                        />

                        <button
                            type="button"
                            className="sidebar-nav-item sidebar-button"
                            onClick={() => {
                                closeMobileSidebar();

                                window.alert(
                                    "Help and support will be available here."
                                );
                            }}
                        >
                            <span className="sidebar-nav-icon">
                                <CircleHelp size={19} />
                            </span>

                            <span>Help</span>
                        </button>

                        <button
                            type="button"
                            className="sidebar-nav-item sidebar-button sidebar-logout"
                            onClick={handleLogout}
                        >
                            <span className="sidebar-nav-icon">
                                <LogOut size={19} />
                            </span>

                            <span>Log out</span>
                        </button>
                    </nav>
                </div>

                {/* =========================
                    FREE PLAN UPGRADE CARD
                   ========================= */}

                {!isPaidPlan && (
                    <div className="sidebar-bottom">
                        <div className="sidebar-plan-card">
                            <div className="sidebar-plan-icon">
                                <Crown size={17} />
                            </div>

                            <div className="sidebar-plan-content">
                                <strong>
                                    {planName}
                                </strong>

                                <span>
                                    {storage} storage
                                </span>
                            </div>

                            <button
                                type="button"
                                className="sidebar-upgrade"
                                onClick={handleUpgrade}
                            >
                                Upgrade
                            </button>
                        </div>
                    </div>
                )}
            </aside>

            <div
                className="mobile-overlay"
                onClick={closeMobileSidebar}
                aria-hidden="true"
            />
        </>
    );
}
