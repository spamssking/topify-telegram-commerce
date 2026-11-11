import axios, { AxiosHeaders } from "axios";

const api = axios.create({
    baseURL: "http://127.0.0.1:8000",
    headers: {
        "Content-Type": "application/json",
    },
});

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem("access_token");

        if (token) {
            if (!config.headers) {
                config.headers = new AxiosHeaders();
            }

            config.headers.set(
                "Authorization",
                `Bearer ${token}`,
            );
        }

        return config;
    },
    (error) => Promise.reject(error),
);

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem("access_token");
        }

        return Promise.reject(error);
    },
);

export function saveToken(token: string) {
    localStorage.setItem("access_token", token);
}

export function getToken() {
    return localStorage.getItem("access_token");
}

export function clearToken() {
    localStorage.removeItem("access_token");
}

export default api;
