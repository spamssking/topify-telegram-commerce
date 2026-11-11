import {
    useEffect,
    useState,
} from "react";

import {
    CheckCircle2,
    Loader2,
    XCircle,
} from "lucide-react";

import {
    useNavigate,
    useSearchParams,
} from "react-router-dom";

import api from "../services/api";
import "./Upgrade.css";



interface PaymentStatus {
    id: string;
    status: string;
    amount: number;
    currency: string;
    provider_reference: string | null;
}


function PaymentCallback() {
    const navigate = useNavigate();

    const [
        searchParams,
    ] = useSearchParams();


    const [
        status,
        setStatus,
    ] = useState<
        "checking" |
        "success" |
        "failed"
    >("checking");


    const [
        message,
        setMessage,
    ] = useState(
        "Confirming your payment...",
    );


    useEffect(() => {
        let cancelled = false;
        let redirectTimer: number | undefined;


        async function confirmPayment() {
            const paymentId =
                localStorage.getItem(
                    "pending_payment_id",
                );

            const reference =
                searchParams.get(
                    "reference",
                );


            if (!paymentId) {
                if (!cancelled) {
                    setStatus("failed");

                    setMessage(
                        reference
                            ? "We received the payment reference, but could not find the local payment record."
                            : "We could not find the payment you were trying to complete.",
                    );
                }

                return;
            }


            const maxAttempts = 15;


            for (
                let attempt = 0;
                attempt < maxAttempts;
                attempt++
            ) {
                if (cancelled) {
                    return;
                }


                try {
                    const response =
                        await api.get<PaymentStatus>(
                            `/api/payments/status/${paymentId}`,
                        );

                    const payment =
                        response.data;


                    if (
                        payment.status ===
                        "PAID"
                    ) {
                        localStorage.removeItem(
                            "pending_payment_id",
                        );

                        localStorage.removeItem(
                            "pending_payment_reference",
                        );


                        if (!cancelled) {
                            setStatus("success");

                            setMessage(
                                "Your payment was successful. Your Pro plan is now being activated.",
                            );
                        }


                        redirectTimer =
                            window.setTimeout(
                                () => {
                                    if (
                                        !cancelled
                                    ) {
                                        navigate(
                                            "/dashboard",
                                            {
                                                replace: true,
                                            },
                                        );
                                    }
                                },
                                2500,
                            );

                        return;
                    }


                    if (
                        payment.status ===
                        "FAILED" ||
                        payment.status ===
                        "CANCELLED"
                    ) {
                        localStorage.removeItem(
                            "pending_payment_id",
                        );

                        localStorage.removeItem(
                            "pending_payment_reference",
                        );


                        if (!cancelled) {
                            setStatus("failed");

                            setMessage(
                                "The payment was not completed. Your account has not been upgraded.",
                            );
                        }

                        return;
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
                }


                await new Promise(
                    (resolve) =>
                        setTimeout(
                            resolve,
                            2000,
                        ),
                );
            }


            if (!cancelled) {
                setStatus("failed");

                setMessage(
                    "We have not received payment confirmation yet. Please check your dashboard shortly. If you were charged, do not pay again.",
                );
            }
        }


        confirmPayment();


        return () => {
            cancelled = true;

            if (
                redirectTimer !==
                undefined
            ) {
                window.clearTimeout(
                    redirectTimer,
                );
            }
        };
    }, [
        navigate,
        searchParams,
    ]);


    return (
        <div className="upgrade-page">

            <div className="payment-result-card">

                {status === "checking" && (
                    <>
                        <div className="payment-result-icon checking">

                            <Loader2
                                size={34}
                                className="spin"
                            />

                        </div>

                        <h1>
                            Confirming payment
                        </h1>
                    </>
                )}


                {status === "success" && (
                    <>
                        <div className="payment-result-icon success">

                            <CheckCircle2
                                size={38}
                            />

                        </div>

                        <h1>
                            Payment successful
                        </h1>
                    </>
                )}


                {status === "failed" && (
                    <>
                        <div className="payment-result-icon failed">

                            <XCircle
                                size={38}
                            />

                        </div>

                        <h1>
                            Payment confirmation
                        </h1>
                    </>
                )}


                <p>
                    {message}
                </p>


                {status === "failed" && (
                    <button
                        type="button"
                        className="primary-button"
                        onClick={() =>
                            navigate(
                                "/dashboard",
                            )
                        }
                    >
                        Go to dashboard
                    </button>
                )}

            </div>

        </div>
    );
}


export default PaymentCallback;
