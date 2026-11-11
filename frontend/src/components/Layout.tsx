import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import "../App.css";

export default function Layout() {
    return (
        <div className="app-shell">
            <Sidebar />

            <div className="app-shell-content">
                <Topbar />

                <main className="app-main">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
