import {
    type ChangeEvent,
    type DragEvent,
    useEffect,
    useRef,
    useState,
} from "react";

import {
    CloudUpload,
    Download,
    File as FileIcon,
    HardDrive,
    Trash2,
    Upload,
    X,
} from "lucide-react";

import {
    useNavigate,
} from "react-router-dom";

import api from "../services/api";
import "./Files.css";


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


interface UserPlan {
    id: string;
    code: string;
    name: string;

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

    storage_quota: number;
    storage_used: number;
    storage_remaining: number;

    plan: UserPlan;
}


function formatBytes(bytes: number) {
    if (!Number.isFinite(bytes) || bytes <= 0) {
        return "0 Bytes";
    }

    const units = [
        "Bytes",
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

    return (
        `${(
            bytes /
            Math.pow(1024, index)
        ).toFixed(index === 0 ? 0 : 1)} ${units[index]}`
    );
}


function formatDate(date: string) {
    const parsed =
        new Date(date);

    if (
        Number.isNaN(
            parsed.getTime(),
        )
    ) {
        return date;
    }

    return parsed.toLocaleString();
}


function Files() {
    const navigate = useNavigate();

    const fileInputRef =
        useRef<HTMLInputElement | null>(
            null,
        );


    const [
        files,
        setFiles,
    ] = useState<FileData[]>([]);


    const [
        user,
        setUser,
    ] = useState<UserData | null>(
        null,
    );


    const [
        loading,
        setLoading,
    ] = useState(true);


    const [
        showUpload,
        setShowUpload,
    ] = useState(false);


    const [
        selectedFile,
        setSelectedFile,
    ] = useState<File | null>(
        null,
    );


    const [
        dragging,
        setDragging,
    ] = useState(false);


    const [
        uploading,
        setUploading,
    ] = useState(false);


    const [
        uploadProgress,
        setUploadProgress,
    ] = useState(0);


    const [
        error,
        setError,
    ] = useState("");


    const [
        uploadLimitMessage,
        setUploadLimitMessage,
    ] = useState("");


    const [
        showUpgradePrompt,
        setShowUpgradePrompt,
    ] = useState(false);


    async function loadData() {
        try {
            setError("");

            const [
                filesResponse,
                userResponse,
            ] = await Promise.all([
                api.get<FileListResponse>(
                    "/api/files",
                    {
                        params: {
                            page: 1,
                            page_size: 100,
                        },
                    },
                ),

                api.get<UserData>(
                    "/api/auth/me",
                ),
            ]);

            setFiles(
                filesResponse.data.items,
            );

            setUser(
                userResponse.data,
            );

        } catch (err: any) {
            if (
                err.response?.status ===
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
                err.response?.data?.detail ||
                "Unable to load files.",
            );

        } finally {
            setLoading(false);
        }
    }


    useEffect(() => {
        loadData();
    }, []);


    function openUploadDialog() {
        setError("");
        setSelectedFile(null);
        setUploadProgress(0);
        setUploadLimitMessage("");
        setShowUpgradePrompt(false);
        setShowUpload(true);

        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }


    function closeUploadDialog() {
        if (uploading) {
            return;
        }

        setShowUpload(false);
        setSelectedFile(null);
        setError("");
        setUploadProgress(0);
        setUploadLimitMessage("");
        setShowUpgradePrompt(false);

        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }


    function selectFile(
        file: File,
    ) {
        setSelectedFile(file);
        setError("");
        setUploadLimitMessage("");
        setShowUpgradePrompt(false);
    }


    function handleFileChange(
        event: ChangeEvent<HTMLInputElement>,
    ) {
        const file =
            event.target.files?.[0];

        if (file) {
            selectFile(file);
        }
    }


    function handleDragOver(
        event: DragEvent<HTMLDivElement>,
    ) {
        event.preventDefault();
        setDragging(true);
    }


    function handleDragLeave(
        event: DragEvent<HTMLDivElement>,
    ) {
        event.preventDefault();
        setDragging(false);
    }


    function handleDrop(
        event: DragEvent<HTMLDivElement>,
    ) {
        event.preventDefault();

        setDragging(false);

        const file =
            event.dataTransfer.files?.[0];

        if (file) {
            selectFile(file);
        }
    }


    async function handleUpload() {
        if (!selectedFile) {
            setError(
                "Please select a file first.",
            );

            return;
        }


        const maxFileSize =
            user?.plan
                ?.max_file_size_bytes;


        if (
            maxFileSize &&
            selectedFile.size >
            maxFileSize
        ) {
            setUploadLimitMessage(
                `This file is too large for your ${user?.plan?.name || "current"} plan. Maximum file size is ${formatBytes(maxFileSize)}.`,
            );

            setShowUpgradePrompt(
                user?.plan?.code === "FREE",
            );

            setError("");

            return;
        }


        if (
            user &&
            user.storage_remaining <
            selectedFile.size
        ) {
            setError(
                `You do not have enough storage space. You have ${formatBytes(user.storage_remaining)} remaining.`,
            );

            return;
        }


        setUploading(true);
        setUploadProgress(0);
        setError("");
        setUploadLimitMessage("");
        setShowUpgradePrompt(false);


        try {
            const formData =
                new FormData();

            formData.append(
                "file",
                selectedFile,
            );


            await api.post(
                "/api/files",
                formData,
                {
                    headers: {
                        "Content-Type":
                            "multipart/form-data",
                    },

                    onUploadProgress:
                        (progressEvent) => {
                            if (
                                progressEvent.total
                            ) {
                                const percentage =
                                    Math.round(
                                        (
                                            progressEvent.loaded /
                                            progressEvent.total
                                        ) *
                                        100,
                                    );

                                setUploadProgress(
                                    percentage,
                                );
                            }
                        },
                },
            );


            setShowUpload(false);
            setSelectedFile(null);
            setUploadProgress(0);
            setUploadLimitMessage("");
            setShowUpgradePrompt(false);


            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }


            await loadData();

        } catch (err: any) {
            const status =
                err.response?.status;

            const detail =
                err.response?.data?.detail;


            if (status === 413) {
                setUploadLimitMessage(
                    detail ||
                    "This file is larger than the maximum size allowed by your current plan.",
                );

                setShowUpgradePrompt(
                    user?.plan?.code ===
                    "FREE",
                );

                setError("");

            } else if (
                status === 400
            ) {
                setError(
                    detail ||
                    "This file cannot be uploaded.",
                );

            } else if (
                status === 403
            ) {
                setError(
                    detail ||
                    "You are not allowed to upload files right now.",
                );

            } else {
                setError(
                    detail ||
                    "Unable to upload file. Please try again.",
                );
            }

        } finally {
            setUploading(false);
        }
    }


    async function handleDownload(
        file: FileData,
    ) {
        try {
            const response =
                await api.get(
                    `/api/files/${file.id}/download`,
                    {
                        responseType:
                            "blob",
                    },
                );


            const blobUrl =
                window.URL.createObjectURL(
                    response.data,
                );


            const link =
                document.createElement(
                    "a",
                );

            link.href =
                blobUrl;

            link.download =
                file.name;

            document.body.appendChild(
                link,
            );

            link.click();

            link.remove();

            window.URL.revokeObjectURL(
                blobUrl,
            );

        } catch (err: any) {
            setError(
                err.response?.data?.detail ||
                "Unable to download file.",
            );
        }
    }


    async function handleDelete(
        file: FileData,
    ) {
        const confirmed =
            window.confirm(
                `Delete "${file.name}"?`,
            );

        if (!confirmed) {
            return;
        }


        try {
            await api.delete(
                `/api/files/${file.id}`,
            );

            await loadData();

        } catch (err: any) {
            setError(
                err.response?.data?.detail ||
                "Unable to delete file.",
            );
        }
    }


    if (loading) {
        return (
            <div className="dashboard-loading">
                Loading your files...
            </div>
        );
    }


    const storagePercentage =
        user &&
            user.storage_quota > 0
            ? Math.min(
                100,
                (
                    user.storage_used /
                    user.storage_quota
                ) * 100,
            )
            : 0;


    return (
        <div className="files-page">

            <header className="files-header">

                <div>
                    <h1>
                        My Files
                    </h1>

                    <p>
                        Upload and manage
                        your files.
                    </p>
                </div>


                <button
                    className="primary-button"
                    onClick={
                        openUploadDialog
                    }
                >
                    <Upload
                        size={18}
                    />

                    Upload File
                </button>

            </header>


            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}


            {user && (
                <section className="files-storage-card">

                    <div className="storage-info">

                        <div>
                            <HardDrive
                                size={22}
                            />

                            <span>
                                Storage
                            </span>
                        </div>


                        <strong>
                            {formatBytes(
                                user.storage_used,
                            )}{" "}
                            /{" "}
                            {formatBytes(
                                user.storage_quota,
                            )}
                        </strong>

                    </div>


                    <div className="progress-background">

                        <div
                            className="progress-fill"
                            style={{
                                width:
                                    `${storagePercentage}%`,
                            }}
                        />

                    </div>


                    <p>
                        {formatBytes(
                            user.storage_remaining,
                        )}{" "}
                        remaining
                    </p>


                    <p>
                        {user.plan.name}
                        {" • "}
                        Maximum file size:{" "}
                        {formatBytes(
                            user.plan.max_file_size_bytes,
                        )}
                    </p>

                </section>
            )}


            <section className="files-card">

                <div className="section-header">

                    <div>
                        <h2>
                            Recent Files
                        </h2>

                        <p>
                            Your uploaded files
                            appear here.
                        </p>
                    </div>

                </div>


                {files.length === 0 ? (

                    <div className="empty-files">

                        <FileIcon
                            size={48}
                        />

                        <h3>
                            No files yet
                        </h3>

                        <p>
                            Upload your first
                            file to get started.
                        </p>

                        <button
                            className="primary-button"
                            onClick={
                                openUploadDialog
                            }
                        >
                            <Upload
                                size={18}
                            />

                            Upload File
                        </button>

                    </div>

                ) : (

                    <div className="file-list">

                        {files.map(
                            (file) => (

                                <div
                                    className="file-row"
                                    key={
                                        file.id
                                    }
                                >

                                    <div className="file-icon">
                                        <FileIcon
                                            size={24}
                                        />
                                    </div>


                                    <div className="file-info">

                                        <strong>
                                            {
                                                file.name
                                            }
                                        </strong>

                                        <span>
                                            {
                                                formatBytes(
                                                    file.size,
                                                )
                                            }
                                            {" • "}
                                            {
                                                formatDate(
                                                    file.created_at,
                                                )
                                            }
                                        </span>

                                    </div>


                                    <span className="file-status">
                                        {
                                            file.status
                                        }
                                    </span>


                                    <button
                                        className="icon-button"
                                        title="Download"
                                        onClick={() =>
                                            handleDownload(
                                                file,
                                            )
                                        }
                                    >
                                        <Download
                                            size={18}
                                        />
                                    </button>


                                    <button
                                        className="icon-button danger"
                                        title="Delete"
                                        onClick={() =>
                                            handleDelete(
                                                file,
                                            )
                                        }
                                    >
                                        <Trash2
                                            size={18}
                                        />
                                    </button>

                                </div>

                            ),
                        )}

                    </div>

                )}

            </section>


            {showUpload && (

                <div
                    className="upload-modal-overlay"
                    onClick={() => {
                        if (!uploading) {
                            closeUploadDialog();
                        }
                    }}
                >

                    <div
                        className="upload-modal"
                        onClick={(event) =>
                            event.stopPropagation()
                        }
                    >

                        <div className="upload-modal-header">

                            <div>

                                <h2>
                                    Upload File
                                </h2>

                                <p>
                                    Choose a file
                                    to upload.
                                </p>

                            </div>


                            <button
                                className="icon-button"
                                onClick={
                                    closeUploadDialog
                                }
                                disabled={
                                    uploading
                                }
                            >
                                <X
                                    size={20}
                                />
                            </button>

                        </div>


                        <div
                            className={
                                `drop-zone ${dragging
                                    ? "dragging"
                                    : ""
                                }`
                            }
                            onDragOver={
                                handleDragOver
                            }
                            onDragLeave={
                                handleDragLeave
                            }
                            onDrop={
                                handleDrop
                            }
                            onClick={() => {
                                if (!uploading) {
                                    fileInputRef.current?.click();
                                }
                            }}
                        >

                            <CloudUpload
                                size={48}
                            />


                            {selectedFile ? (

                                <>
                                    <h3>
                                        {
                                            selectedFile.name
                                        }
                                    </h3>

                                    <p>
                                        {
                                            formatBytes(
                                                selectedFile.size,
                                            )
                                        }
                                    </p>
                                </>

                            ) : (

                                <>
                                    <h3>
                                        Drag & drop
                                        your file here
                                    </h3>

                                    <p>
                                        or click to
                                        choose a file
                                    </p>
                                </>

                            )}


                            <input
                                ref={
                                    fileInputRef
                                }
                                type="file"
                                hidden
                                onChange={
                                    handleFileChange
                                }
                            />

                        </div>


                        {uploading && (

                            <div className="upload-progress">

                                <div className="progress-header">

                                    <span>
                                        Uploading...
                                    </span>

                                    <span>
                                        {
                                            uploadProgress
                                        }%
                                    </span>

                                </div>


                                <div className="progress-background">

                                    <div
                                        className="progress-fill"
                                        style={{
                                            width:
                                                `${uploadProgress}%`,
                                        }}
                                    />

                                </div>

                            </div>

                        )}


                        {showUpgradePrompt && (

                            <div className="upload-limit-prompt">

                                <div>

                                    <strong>
                                        File exceeds
                                        your plan
                                        limit
                                    </strong>

                                    <p>
                                        {
                                            uploadLimitMessage
                                        }
                                    </p>

                                    <p>
                                        Upgrade to
                                        Pro for a
                                        higher
                                        file-size
                                        limit and
                                        more storage.
                                    </p>

                                </div>


                                <button
                                    className="primary-button"
                                    onClick={() =>
                                        navigate(
                                            "/upgrade",
                                        )
                                    }
                                >
                                    Upgrade to Pro
                                </button>

                            </div>

                        )}


                        <div className="upload-modal-footer">

                            <button
                                className="secondary-button"
                                onClick={
                                    closeUploadDialog
                                }
                                disabled={
                                    uploading
                                }
                            >
                                Cancel
                            </button>


                            <button
                                className="primary-button"
                                onClick={
                                    handleUpload
                                }
                                disabled={
                                    !selectedFile ||
                                    uploading
                                }
                            >

                                <Upload
                                    size={18}
                                />

                                {uploading
                                    ? "Uploading..."
                                    : "Upload"}

                            </button>

                        </div>

                    </div>

                </div>

            )}

        </div>
    );
}


export default Files;
