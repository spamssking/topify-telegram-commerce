import {
    useEffect,
    useState,
} from "react";

import {
    Check,
    CreditCard,
    Loader2,
    ShieldCheck,
    Sparkles,
} from "lucide-react";

import {
    useNavigate,
} from "react-router-dom";

import api from "../services/api";
import "./Upgrade.css";


interface Plan {
    id: string;
    code: string;
    name: string;
    description: string | null;

    storage_quota_bytes: number;
    max_file_size_bytes: number;
    max_files: number | null;

    thumbnail_enabled: boolean;

    price: number;
    currency: string;
    billing_interval: string | null;

    sort_order: number;

    is_active: boolean;
    is_default: boolean;
}



interface CheckoutResponse {
    payment_id: string;
    reference: string;
    authorization_url: string;
    access_code: string;
}


interface CurrentUser {
    id: string;
    email: string;
    full_name: string | null;

    plan_id: string;

    is_active: boolean;
    is_verified: boolean;
}


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
            Math.log(bytes) /
            Math.log(1024),
        ),
        units.length - 1,
    );

    const value =
        bytes /
        Math.pow(1024, index);

    return `${value.toFixed(1)} ${units[index]}`;
}


function formatPrice(
    amount: number,
    currency: string,
) {
    const value =
        amount / 100;

    return new Intl.NumberFormat(
        "en-NG",
        {
            style: "currency",
            currency,
            maximumFractionDigits: 0,
        },
    ).format(value);
}


function Upgrade() {
    const navigate = useNavigate();

    const [plans, setPlans] =
        useState<Plan[]>([]);

    const [selectedPlan, setSelectedPlan] =
        useState<Plan | null>(null);

    const [autoRenew, setAutoRenew] =
        useState(true);

    const [loading, setLoading] =
        useState(true);

    const [checkoutLoading, setCheckoutLoading] =
        useState(false);

    const [error, setError] =
        useState("");

    const [user, setUser] =
        useState<CurrentUser | null>(null);


    useEffect(() => {
        let mounted = true;

        async function loadPage() {
            try {
                setLoading(true);
                setError("");

                const [
                    userResponse,
                    plansResponse,
                ] = await Promise.all([
                    api.get<CurrentUser>(
                        "/api/auth/me",
                    ),

                    api.get<Plan[]>(
                        "/api/plans",
                    ),
                ]);

                if (!mounted) {
                    return;
                }

                const currentUser =
                    userResponse.data;

                const allPlans =
                    plansResponse.data;

                setUser(currentUser);

                const paidPlans =
                    allPlans.filter(
                        (plan) =>
                            plan.is_active !== false &&
                            plan.price > 0,
                    );

                setPlans(paidPlans);

                const currentPlan =
                    allPlans.find(
                        (plan) =>
                            plan.id ===
                            currentUser.plan_id,
                    );

                if (
                    currentPlan?.code === "PRO"
                ) {
                    return;
                }

                if (
                    paidPlans.length > 0
                ) {
                    setSelectedPlan(
                        paidPlans[0],
                    );
                }
            } catch (err: any) {
                if (
                    err.response?.status ===
                    401
                ) {
                    navigate(
                        "/login",
                        {
                            replace: true,
                        },
                    );

                    return;
                }

                if (mounted) {
                    setError(
                        err.response?.data?.detail ||
                        "Unable to load upgrade information.",
                    );
                }
            } finally {
                if (mounted) {
                    setLoading(false);
                }
            }
        }

        loadPage();

        return () => {
            mounted = false;
        };
    }, [navigate]);


    async function handleCheckout() {
        if (!selectedPlan) {
            setError(
                "Please select a plan.",
            );

            return;
        }

        setCheckoutLoading(true);
        setError("");

        try {
            const response =
                await api.post<CheckoutResponse>(
                    "/api/payments/checkout",
                    {
                        plan_id:
                            selectedPlan.id,

                        auto_renew:
                            autoRenew,
                    },
                );

            localStorage.setItem(
                "pending_payment_id",
                response.data.payment_id,
            );

            localStorage.setItem(
                "pending_payment_reference",
                response.data.reference,
            );

            window.location.href =
                response.data.authorization_url;
        } catch (err: any) {
            setError(
                err.response?.data?.detail ||
                "Unable to start payment.",
            );

            setCheckoutLoading(false);
        }
    }


    if (loading) {
        return (
            <div className="dashboard-loading">
                Loading upgrade options...
            </div>
        );
    }


    const isAlreadyPro =
        user &&
        plans.some(
            (plan) =>
                plan.id === user.plan_id &&
                plan.code === "PRO",
        );


    if (isAlreadyPro) {
        return (
            <div className="upgrade-page">

                <div className="upgrade-header">

                    <div className="upgrade-icon success">
                        <Check size={28} />
                    </div>

                    <h1>
                        Already upgraded to Pro
                    </h1>

                    <p>
                        Your account is already
                        using the Pro storage plan.
                    </p>

                </div>


                <div className="already-pro-card">

                    <div className="already-pro-icon">
                        <Sparkles
                            size={26}
                        />
                    </div>

                    <div>

                        <h2>
                            Pro plan active
                        </h2>

                        <p>
                            You already have access
                            to your Pro storage
                            benefits.
                        </p>

                    </div>

                </div>


                <button
                    type="button"
                    className="primary-button"
                    onClick={() =>
                        navigate(
                            "/dashboard",
                        )
                    }
                >
                    Back to dashboard
                </button>

            </div>
        );
    }


    return (
        <div className="upgrade-page">

            <div className="upgrade-header">

                <div className="upgrade-icon">
                    <Sparkles
                        size={28}
                    />
                </div>

                <h1>
                    Upgrade your storage
                </h1>

                <p>
                    Get more space and keep
                    your files securely stored.
                </p>

            </div>


            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}


            {plans.length === 0 ? (
                <div className="empty-files">

                    <h3>
                        No paid plans available
                    </h3>

                    <p>
                        Please try again later.
                    </p>

                </div>
            ) : (
                <>
                    <div className="plans-grid">

                        {plans.map(
                            (plan) => {

                                const selected =
                                    selectedPlan?.id ===
                                    plan.id;

                                return (
                                    <button
                                        type="button"
                                        key={plan.id}
                                        className={
                                            `plan-card ${selected
                                                ? "selected"
                                                : ""
                                            }`
                                        }
                                        onClick={() =>
                                            setSelectedPlan(
                                                plan,
                                            )
                                        }
                                    >

                                        {selected && (
                                            <div className="plan-selected">
                                                Selected
                                            </div>
                                        )}


                                        <div className="plan-card-icon">
                                            <Sparkles
                                                size={22}
                                            />
                                        </div>


                                        <h2>
                                            {plan.name}
                                        </h2>


                                        {plan.description && (
                                            <p>
                                                {
                                                    plan.description
                                                }
                                            </p>
                                        )}


                                        <div className="plan-price">

                                            {formatPrice(
                                                plan.price,
                                                plan.currency,
                                            )}

                                            <span>
                                                /
                                                {
                                                    plan.billing_interval ===
                                                        "MONTH"
                                                        ? "month"
                                                        : plan.billing_interval?.toLowerCase() ||
                                                        "billing period"
                                                }
                                            </span>

                                        </div>


                                        <div className="plan-features">

                                            <div>
                                                <Check
                                                    size={18}
                                                />

                                                <span>
                                                    {
                                                        formatBytes(
                                                            plan.storage_quota_bytes,
                                                        )
                                                    }{" "}
                                                    storage
                                                </span>
                                            </div>


                                            <div>
                                                <Check
                                                    size={18}
                                                />

                                                <span>
                                                    Up to{" "}
                                                    {
                                                        formatBytes(
                                                            plan.max_file_size_bytes,
                                                        )
                                                    }{" "}
                                                    per file
                                                </span>
                                            </div>


                                            {plan.max_files && (
                                                <div>
                                                    <Check
                                                        size={18}
                                                    />

                                                    <span>
                                                        Up to{" "}
                                                        {
                                                            plan.max_files
                                                        }{" "}
                                                        files
                                                    </span>
                                                </div>
                                            )}

                                        </div>

                                    </button>
                                );
                            },
                        )}

                    </div>


                    <div className="checkout-card">

                        <div className="checkout-row">

                            <div>

                                <strong>
                                    Automatic renewal
                                </strong>

                                <p>
                                    Automatically renew
                                    your plan each month.
                                </p>

                            </div>


                            <button
                                type="button"
                                className={
                                    `toggle ${autoRenew
                                        ? "active"
                                        : ""
                                    }`
                                }
                                onClick={() =>
                                    setAutoRenew(
                                        (current) =>
                                            !current,
                                    )
                                }
                                aria-pressed={
                                    autoRenew
                                }
                            >
                                <span />
                            </button>

                        </div>


                        <div className="checkout-security">

                            <ShieldCheck
                                size={20}
                            />

                            <span>
                                Secure payment
                                powered by Paystack
                            </span>

                        </div>


                        <button
                            type="button"
                            className="primary-button checkout-button"
                            onClick={
                                handleCheckout
                            }
                            disabled={
                                checkoutLoading ||
                                !selectedPlan
                            }
                        >

                            {checkoutLoading ? (
                                <>
                                    <Loader2
                                        size={18}
                                        className="spin"
                                    />

                                    Redirecting...
                                </>
                            ) : (
                                <>
                                    <CreditCard
                                        size={18}
                                    />

                                    Continue to
                                    payment
                                </>
                            )}

                        </button>

                    </div>
                </>
            )}

        </div>
    );
}


export default Upgrade;
