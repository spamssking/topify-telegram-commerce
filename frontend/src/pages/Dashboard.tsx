import {
    ArrowRight,
    CheckCircle2,
    ChevronRight,
    Cloud,
    FileText,
    Image as ImageIcon,
    Music2,
    PlaySquare,
    Sparkles,
    Upload,
} from "lucide-react";

import {
    useEffect,
    useState,
} from "react";

import {
    useNavigate,
} from "react-router-dom";

import api from "../services/api";

import "./Dashboard.css";


interface UserPlan {
    id: string;
    code: string;
    name: string;
    description?: string | null;

    storage_quota?: number;
    storage_quota_bytes?: number;

    max_file_size_bytes: number;

    max_files?: number | null;

    thumbnail_enabled?: boolean;

    price?: number;
    currency?: string;

    billing_interval?: string | null;
}


interface UserData {
    id?: string;

    email?: string;

    full_name?: string | null;

    plan_id?: string;

    storage_quota: number;
    storage_used: number;
    storage_remaining: number;

    plan: UserPlan;

    is_active?: boolean;
    is_verified?: boolean;
}


interface FileData {
    id: string;
    name: string;
    mime_type: string | null;
    size: number;
    sha256: string;
    status: string;
    created_at: string;
}


interface FileListResponse {
    items: FileData[];
    page: number;
    page_size: number;
    total: number;
}


type StorageCategory = {
    label: string;
    amount: number;
    percentage: number;
    color: string;
    icon: React.ReactNode;
};


function formatBytes(bytes: number) {
    if (!Number.isFinite(bytes) || bytes <= 0) {
        return "0 B";
    }

    const units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ];

    const index = Math.min(
        Math.floor(
            Math.log(bytes) / Math.log(1024),
        ),
        units.length - 1,
    );

    const value =
        bytes / Math.pow(1024, index);

    if (index === 0) {
        return `${Math.round(value)} ${units[index]}`;
    }

    return `${value.toFixed(1)} ${units[index]}`;
}


function getFirstName(
    fullName: string | null | undefined,
    email: string | undefined,
) {
    if (fullName?.trim()) {
        return fullName
            .trim()
            .split(/\s+/)[0];
    }

    if (email) {
        return email.split("@")[0];
    }

    return "there";
}


function getFileCategory(
    file: FileData,
):
    | "Videos"
    | "Audio"
    | "Documents"
    | "Images"
    | "Other" {
    const mime =
        file.mime_type?.toLowerCase() || "";

    if (mime.startsWith("video/")) {
        return "Videos";
    }

    if (mime.startsWith("audio/")) {
        return "Audio";
    }

    if (mime.startsWith("image/")) {
        return "Images";
    }

    if (
        mime.includes("pdf") ||
        mime.includes("document") ||
        mime.includes("text") ||
        mime.includes("word") ||
        mime.includes("excel") ||
        mime.includes("spreadsheet") ||
        mime.includes("presentation") ||
        mime.includes("csv")
    ) {
        return "Documents";
    }

    return "Other";
}


function getCategoryPercentage(
    amount: number,
    total: number,
) {
    if (amount <= 0 || total <= 0) {
        return 0;
    }

    return Math.min(
        100,
        (amount / total) * 100,
    );
}


export default function Dashboard() {
    const navigate = useNavigate();

    const [
        user,
        setUser,
    ] = useState<UserData | null>(null);

    const [
        files,
        setFiles,
    ] = useState<FileData[]>([]);

    const [
        loading,
        setLoading,
    ] = useState(true);

    const [
        error,
        setError,
    ] = useState("");


    useEffect(() => {
        let mounted = true;

        async function loadDashboard() {
            try {
                setLoading(true);
                setError("");

                const [
                    userResponse,
                    filesResponse,
                ] = await Promise.all([
                    api.get<UserData>(
                        "/api/auth/me",
                    ),

                    api.get<FileListResponse>(
                        "/api/files",
                        {
                            params: {
                                page: 1,
                                page_size: 100,
                            },
                        },
                    ),
                ]);

                if (!mounted) {
                    return;
                }

                setUser(
                    userResponse.data,
                );

                setFiles(
                    filesResponse.data.items,
                );
            } catch (err: unknown) {
                if (!mounted) {
                    return;
                }

                const axiosError = err as {
                    response?: {
                        status?: number;
                        data?: {
                            detail?: string;
                        };
                    };
                };

                if (
                    axiosError.response?.status ===
                    401
                ) {
                    localStorage.removeItem(
                        "access_token",
                    );

                    navigate(
                        "/login",
                        {
                            replace: true,
                        },
                    );

                    return;
                }

                setError(
                    axiosError.response?.data?.detail ||
                    "Unable to load your dashboard.",
                );
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        }

        loadDashboard();

        return () => {
            mounted = false;
        };
    }, [navigate]);


    function handleLogout() {
        localStorage.removeItem(
            "access_token",
        );

        localStorage.removeItem(
            "token",
        );

        localStorage.removeItem(
            "pending_payment_id",
        );

        localStorage.removeItem(
            "pending_payment_reference",
        );

        navigate(
            "/login",
            {
                replace: true,
            },
        );
    }


    if (loading) {
        return (
            <div className="dashboard-loading">
                Loading your dashboard...
            </div>
        );
    }


    if (error) {
        return (
            <div className="cloud-dashboard">
                <main className="dashboard-content">
                    <div className="error-message">
                        {error}
                    </div>

                    <button
                        type="button"
                        className="primary-button"
                        onClick={() =>
                            window.location.reload()
                        }
                    >
                        Try again
                    </button>
                </main>
            </div>
        );
    }


    if (!user) {
        return (
            <div className="dashboard-loading">
                Unable to load your account.
            </div>
        );
    }


    const userName =
        getFirstName(
            user.full_name,
            user.email,
        );


    const planName =
        user.plan?.name ||
        "Free";


    const isPaidPlan =
        user.plan?.code !== "FREE";


    const storageLimit =
        user.storage_quota ||
        user.plan?.storage_quota_bytes ||
        user.plan?.storage_quota ||
        0;


    const usedStorage =
        Math.max(
            0,
            user.storage_used || 0,
        );


    const remainingStorage =
        Math.max(
            0,
            user.storage_remaining ??
            storageLimit - usedStorage,
        );


    const storagePercentage =
        storageLimit > 0
            ? Math.min(
                100,
                (
                    usedStorage /
                    storageLimit
                ) *
                100,
            )
            : 0;


    const categoryTotals: Record<
        | "Videos"
        | "Audio"
        | "Documents"
        | "Images"
        | "Other",
        number
    > = {
        Videos: 0,
        Audio: 0,
        Documents: 0,
        Images: 0,
        Other: 0,
    };


    for (const file of files) {
        const category =
            getFileCategory(file);

        categoryTotals[category] +=
            file.size || 0;
    }


    const storageCategories: StorageCategory[] = [
        {
            label: "Videos",
            amount: categoryTotals.Videos,
            percentage:
                getCategoryPercentage(
                    categoryTotals.Videos,
                    usedStorage,
                ),
            color: "#6366f1",
            icon: (
                <PlaySquare
                    size={18}
                />
            ),
        },

        {
            label: "Audio",
            amount: categoryTotals.Audio,
            percentage:
                getCategoryPercentage(
                    categoryTotals.Audio,
                    usedStorage,
                ),
            color: "#8b5cf6",
            icon: (
                <Music2
                    size={18}
                />
            ),
        },

        {
            label: "Documents",
            amount: categoryTotals.Documents,
            percentage:
                getCategoryPercentage(
                    categoryTotals.Documents,
                    usedStorage,
                ),
            color: "#0ea5e9",
            icon: (
                <FileText
                    size={18}
                />
            ),
        },

        {
            label: "Images",
            amount: categoryTotals.Images,
            percentage:
                getCategoryPercentage(
                    categoryTotals.Images,
                    usedStorage,
                ),
            color: "#10b981",
            icon: (
                <ImageIcon
                    size={18}
                />
            ),
        },
    ];


    return (
        <div className="cloud-dashboard">

            <main className="dashboard-content">

                {/* HEADER */}

                <header className="dashboard-top">

                    <div>

                        <p className="dashboard-eyebrow">
                            CloudBox dashboard
                        </p>

                        <h1>
                            Hi, {userName} 👋
                        </h1>

                        <p className="dashboard-subtitle">
                            Here's an overview of
                            your cloud storage.
                        </p>

                    </div>


                    <button
                        type="button"
                        className="dashboard-upload-button"
                        onClick={() =>
                            navigate("/files")
                        }
                    >
                        <Upload
                            size={18}
                        />

                        Upload files
                    </button>

                </header>


                {/* CURRENT PLAN */}

                <section className="current-plan-card">

                    <div className="current-plan-main">

                        <div className="current-plan-icon">
                            <Sparkles
                                size={22}
                            />
                        </div>


                        <div>

                            <span className="card-label">
                                Current plan
                            </span>

                            <h2>
                                {planName} plan
                            </h2>

                            <p>
                                You're currently
                                using CloudBox with{" "}
                                <strong>
                                    {formatBytes(
                                        usedStorage,
                                    )}
                                </strong>{" "}
                                of{" "}
                                <strong>
                                    {formatBytes(
                                        storageLimit,
                                    )}
                                </strong>{" "}
                                used.
                            </p>

                        </div>

                    </div>


                    <div className="current-plan-action">

                        <span className="plan-status">
                            <CheckCircle2
                                size={15}
                            />

                            Active
                        </span>


                        <button
                            type="button"
                            onClick={() =>
                                navigate(
                                    isPaidPlan
                                        ? "/dashboard"
                                        : "/upgrade",
                                )
                            }
                            className="plan-details-button"
                        >
                            {isPaidPlan
                                ? "Plan active"
                                : "View plans"}

                            <ChevronRight
                                size={17}
                            />
                        </button>

                    </div>

                </section>


                {/* STORAGE */}

                <section className="dashboard-section">

                    <div className="section-heading">

                        <div>

                            <h2>
                                Storage
                            </h2>

                            <p>
                                See how your
                                CloudBox space
                                is being used.
                            </p>

                        </div>


                        <button
                            type="button"
                            className="text-button"
                            onClick={() =>
                                navigate(
                                    "/files",
                                )
                            }
                        >
                            Manage storage

                            <ArrowRight
                                size={16}
                            />
                        </button>

                    </div>


                    <div className="storage-overview-grid">

                        {/* STORAGE CIRCLE */}

                        <div className="storage-usage-card">

                            <div className="storage-circle-wrapper">

                                <div
                                    className="storage-circle"
                                    style={{
                                        background:
                                            `conic-gradient(
                                                #6366f1 ${storagePercentage}%,
                                                #edf0f7 ${storagePercentage}% 100%
                                            )`,
                                    }}
                                >

                                    <div className="storage-circle-inner">

                                        <Cloud
                                            size={25}
                                        />

                                        <strong>
                                            {storagePercentage < 0.1
                                                ? "<0.1%"
                                                : `${storagePercentage.toFixed(
                                                    1,
                                                )}%`}
                                        </strong>

                                        <span>
                                            used
                                        </span>

                                    </div>

                                </div>

                            </div>


                            <div className="storage-usage-info">

                                <span className="card-label">
                                    Available storage
                                </span>

                                <h3>
                                    {formatBytes(
                                        remainingStorage,
                                    )}
                                </h3>

                                <p>
                                    of{" "}
                                    {formatBytes(
                                        storageLimit,
                                    )}{" "}
                                    total storage
                                </p>

                            </div>

                        </div>


                        {/* BREAKDOWN */}

                        <div className="storage-breakdown-card">

                            <div className="breakdown-header">

                                <div>

                                    <h3>
                                        Storage
                                        breakdown
                                    </h3>

                                    <p>
                                        What's taking
                                        up your space
                                    </p>

                                </div>

                            </div>


                            <div className="storage-categories">

                                {storageCategories.map(
                                    (
                                        category,
                                    ) => (

                                        <div
                                            className="storage-category"
                                            key={
                                                category.label
                                            }
                                        >

                                            <div
                                                className="storage-category-icon"
                                                style={{
                                                    color:
                                                        category.color,

                                                    background:
                                                        `${category.color}12`,
                                                }}
                                            >
                                                {
                                                    category.icon
                                                }
                                            </div>


                                            <div className="storage-category-info">

                                                <div className="storage-category-top">

                                                    <strong>
                                                        {
                                                            category.label
                                                        }
                                                    </strong>

                                                    <span>
                                                        {
                                                            formatBytes(
                                                                category.amount,
                                                            )
                                                        }
                                                    </span>

                                                </div>


                                                <div className="category-bar">

                                                    <span
                                                        style={{
                                                            width:
                                                                category.percentage >
                                                                    0
                                                                    ? `${Math.max(
                                                                        category.percentage,
                                                                        1,
                                                                    )}%`
                                                                    : "0%",

                                                            background:
                                                                category.color,
                                                        }}
                                                    />

                                                </div>

                                            </div>

                                        </div>

                                    ),
                                )}

                            </div>

                        </div>

                    </div>

                </section>


                {/* MANAGEMENT */}

                <section className="dashboard-section">

                    <div className="section-heading">

                        <div>

                            <h2>
                                Manage your
                                storage
                            </h2>

                            <p>
                                Keep your CloudBox
                                account organized.
                            </p>

                        </div>

                    </div>


                    <div className="dashboard-tools">

                        <button
                            type="button"
                            className="dashboard-tool-card"
                            onClick={() =>
                                navigate(
                                    "/files",
                                )
                            }
                        >

                            <div className="tool-icon blue">
                                <Cloud
                                    size={20}
                                />
                            </div>


                            <div>

                                <strong>
                                    Manage your
                                    files
                                </strong>

                                <p>
                                    Browse, download
                                    and organize
                                    everything in
                                    your cloud.
                                </p>

                            </div>


                            <ChevronRight
                                size={19}
                            />

                        </button>


                        <button
                            type="button"
                            className="dashboard-tool-card"
                            onClick={() =>
                                navigate(
                                    "/cleanup",
                                )
                            }
                        >

                            <div className="tool-icon green">
                                <Sparkles
                                    size={20}
                                />
                            </div>


                            <div>

                                <strong>
                                    Clean up storage
                                </strong>

                                <p>
                                    Find large or
                                    unnecessary
                                    files and free
                                    up space.
                                </p>

                            </div>


                            <ChevronRight
                                size={19}
                            />

                        </button>

                    </div>

                </section>


                {/* UPDATES */}

                <section className="dashboard-section">

                    <div className="section-heading">

                        <div>

                            <h2>
                                What's new
                            </h2>

                            <p>
                                New features and
                                useful CloudBox
                                updates.
                            </p>

                        </div>

                    </div>


                    <div className="updates-grid">

                        <article className="update-card update-purple">

                            <div className="update-icon">
                                <Sparkles
                                    size={20}
                                />
                            </div>


                            <div>

                                <span className="update-label">
                                    CloudBox
                                </span>

                                <h3>
                                    A simpler way
                                    to manage your
                                    files
                                </h3>

                                <p>
                                    Your files,
                                    storage and
                                    account settings
                                    are easier to
                                    access from one
                                    place.
                                </p>

                            </div>

                        </article>


                        <article className="update-card update-blue">

                            <div className="update-icon">
                                <Cloud
                                    size={20}
                                />
                            </div>


                            <div>

                                <span className="update-label">
                                    Storage
                                </span>

                                <h3>
                                    Your storage
                                    at a glance
                                </h3>

                                <p>
                                    See exactly how
                                    your cloud
                                    storage is being
                                    used from the
                                    dashboard.
                                </p>

                            </div>

                        </article>

                    </div>

                </section>


                {/* LOGOUT */}

                <section className="dashboard-footer">

                    <button
                        type="button"
                        className="dashboard-logout"
                        onClick={
                            handleLogout
                        }
                    >
                        Log out
                    </button>

                </section>

            </main>

        </div>
    );
}
