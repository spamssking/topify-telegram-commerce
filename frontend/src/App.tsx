import {
    BrowserRouter,
    Navigate,
    Route,
    Routes,
} from "react-router-dom";

import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";

import Login from "./pages/Login";
import Register from "./pages/Register";
import VerifyEmail from "./pages/VerifyEmail";
import Dashboard from "./pages/Dashboard";
import Files from "./pages/Files";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";
import Upgrade from "./pages/Upgrade";
import PaymentCallback from "./pages/PaymentCallback";
import Cleanup from "./pages/Cleanup";


function App() {
    return (
        <BrowserRouter>
            <Routes>
                {/* Public routes */}
                <Route
                    path="/"
                    element={<Navigate to="/login" replace />}
                />

                <Route
                    path="/login"
                    element={<Login />}
                />

                <Route
                    path="/register"
                    element={<Register />}
                />

                <Route
                    path="/verify-email"
                    element={<VerifyEmail />}
                />

                {/* Protected application */}
                <Route element={<ProtectedRoute />}>
                    <Route element={<Layout />}>
                        <Route
                            path="/dashboard"
                            element={<Dashboard />}
                        />

                        <Route
                            path="/files"
                            element={<Files />}
                        />

                        <Route
                            path="/cleanup"
                            element={<Cleanup />}
                        />

                        <Route
                            path="/profile"
                            element={<Profile />}
                        />

                        <Route
                            path="/settings"
                            element={<Settings />}
                        />

                        <Route
                            path="/upgrade"
                            element={<Upgrade />}
                        />
                    </Route>
                </Route>

                {/* Payment callback */}
                <Route
                    path="/payment/callback"
                    element={<PaymentCallback />}
                />

                <Route
                    path="*"
                    element={<Navigate to="/login" replace />}
                />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
