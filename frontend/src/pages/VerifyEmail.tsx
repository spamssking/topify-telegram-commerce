import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";

type VerificationState = "verifying" | "success" | "error";

function VerifyEmail() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    const [state, setState] =
        useState<VerificationState>("verifying");

    const [message, setMessage] = useState(
        "Verifying your email address..."
    );

    const hasVerified = useRef(false);

    useEffect(() => {
        if (hasVerified.current) {
            return;
        }

        hasVerified.current = true;

        const verifyEmail = async () => {
            const token = searchParams.get("token");

            if (!token) {
                setState("error");
                setMessage("Verification link is invalid.");
                return;
            }

            try {
                const response = await fetch(
                    `http://127.0.0.1:8000/api/auth/verify-email?token=${encodeURIComponent(token)}`,
                    {
                        method: "GET",
                    }
                );

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(
                        data.detail || "Unable to verify your email."
                    );
                }

                setState("success");
                setMessage(
                    "Your email has been verified successfully."
                );

                // Give the user a moment to see the success message,
                // then take them to the login page.
                setTimeout(() => {
                    navigate("/login");
                }, 1500);
            } catch (error) {
                setState("error");

                if (error instanceof Error) {
                    setMessage(error.message);
                } else {
                    setMessage("Unable to verify your email.");
                }
            }
        };

        verifyEmail();
    }, [searchParams, navigate]);

    return (
        <div
            style={{
                minHeight: "100vh",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "#f6f8fc",
                padding: "24px",
            }}
        >
            <div
                style={{
                    width: "100%",
                    maxWidth: "460px",
                    background: "#ffffff",
                    borderRadius: "16px",
                    padding: "40px",
                    textAlign: "center",
                    boxShadow: "0 10px 40px rgba(0, 0, 0, 0.08)",
                }}
            >
                <h1
                    style={{
                        marginBottom: "12px",
                        color: "#172033",
                    }}
                >
                    Cloud Storage
                </h1>

                {state === "verifying" && (
                    <>
                        <div
                            style={{
                                fontSize: "40px",
                                marginBottom: "20px",
                            }}
                        >
                            ⏳
                        </div>

                        <h2>Verifying your email</h2>

                        <p style={{ color: "#667085" }}>
                            Please wait while we verify your account.
                        </p>
                    </>
                )}

                {state === "success" && (
                    <>
                        <div
                            style={{
                                fontSize: "40px",
                                marginBottom: "20px",
                            }}
                        >
                            ✅
                        </div>

                        <h2>Email verified!</h2>

                        <p style={{ color: "#667085" }}>
                            {message}
                        </p>

                        <p
                            style={{
                                color: "#667085",
                                fontSize: "14px",
                            }}
                        >
                            Taking you to login...
                        </p>
                    </>
                )}

                {state === "error" && (
                    <>
                        <div
                            style={{
                                fontSize: "40px",
                                marginBottom: "20px",
                            }}
                        >
                            !
                        </div>

                        <h2>Verification failed</h2>

                        <p style={{ color: "#667085" }}>
                            {message}
                        </p>

                        <Link
                            to="/login"
                            style={{
                                display: "inline-block",
                                marginTop: "20px",
                                padding: "12px 24px",
                                borderRadius: "8px",
                                background: "#2563eb",
                                color: "#ffffff",
                                textDecoration: "none",
                            }}
                        >
                            Go to Login
                        </Link>
                    </>
                )}
            </div>
        </div>
    );
}

export default VerifyEmail;