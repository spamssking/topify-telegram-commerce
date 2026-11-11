import {
    AlertTriangle,
    ArrowLeft,
    Calendar,
    CheckCircle2,
    Copy,
    File,
    HardDrive,
    Image,
    Music,
    Trash2,
    Video,
    X,
} from "lucide-react";

import {
    useEffect,
    useMemo,
    useState,
} from "react";

import {
    useNavigate,
} from "react-router-dom";

import api from "../services/api";

import "./Cleanup.css";


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
    storage_quota: number;
    max_file_size_bytes: number;
}


interface UserData {
    storage_quota: number;
    storage_used: number;
    storage_remaining: number;
    plan: UserPlan;
}


type SuggestionType =
    | "large"
    | "old"
    | "duplicate"
    | "media"
    | "other";


interface Suggestion {
    type: SuggestionType;
    title: string;
    description: string;
    files: FileData[];
    bytes: number;
}


function formatBytes(bytes: number) {
    if (bytes === 0) {
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
            Math.log(bytes) / Math.log(1024),
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
    return new Date(date).toLocaleDateString(
        undefined,
        {
            year: "numeric",
            month: "short",
            day: "numeric",
        },
    );
}


function getFileCategory(
    mimeType: string | null,
): "image" | "video" | "audio" | "other" {
    if (!mimeType) {
        return "other";
    }

    if (mimeType.startsWith("image/")) {
        return "image";
    }

    if (mimeType.startsWith("video/")) {
        return "video";
    }

    if (mimeType.startsWith("audio/")) {
        return "audio";
    }

    return "other";
}


function FileTypeIcon({
    mimeType,
}: {
    mimeType: string | null;
}) {
    const category =
        getFileCategory(mimeType);

    if (category === "image") {
        return <Image size={20} />;
    }

    if (category === "video") {
        return <Video size={20} />;
    }

    if (category === "audio") {
        return <Music size={20} />;
    }

    return <File size={20} />;
}


function Cleanup() {
    const navigate = useNavigate();

    const [files, setFiles] =
        useState<FileData[]>([]);

    const [user, setUser] =
        useState<UserData | null>(null);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState("");

    const [selectedSuggestion, setSelectedSuggestion] =
        useState<Suggestion | null>(null);

    const [deletingId, setDeletingId] =
        useState<string | null>(null);

    const [selectedFiles, setSelectedFiles] =
        useState<Set<string>>(new Set());

    async function loadData() {
        try {
            setLoading(true);
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
                err.response?.status === 401
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
                "Unable to analyze your storage.",
            );

        } finally {
            setLoading(false);
        }
    }


    useEffect(() => {
        loadData();
    }, []);


    /*
     * Files larger than this are considered
     * worth reviewing.
     *
     * This is a suggestion only.
     */
    const largeFiles = useMemo(() => {
        return [...files]
            .filter(
                (file) =>
                    file.size >=
                    100 * 1024 * 1024,
            )
            .sort(
                (a, b) =>
                    b.size - a.size,
            );
    }, [files]);


    /*
     * Files older than 180 days.
     */
    const oldFiles = useMemo(() => {
        const cutoff =
            Date.now() -
            180 *
            24 *
            60 *
            60 *
            1000;

        return [...files]
            .filter(
                (file) =>
                    new Date(
                        file.created_at,
                    ).getTime() < cutoff,
            )
            .sort(
                (a, b) =>
                    new Date(
                        a.created_at,
                    ).getTime() -
                    new Date(
                        b.created_at,
                    ).getTime(),
            );
    }, [files]);


    /*
     * Duplicate files are identified by
     * their SHA-256 hash.
     */
    const duplicateGroups = useMemo(() => {
        const groups =
            new Map<
                string,
                FileData[]
            >();

        for (const file of files) {
            if (!file.sha256) {
                continue;
            }

            const existing =
                groups.get(file.sha256) ||
                [];

            existing.push(file);

            groups.set(
                file.sha256,
                existing,
            );
        }

        return Array.from(
            groups.values(),
        ).filter(
            (group) =>
                group.length > 1,
        );
    }, [files]);


    const duplicateFiles = useMemo(() => {
        return duplicateGroups.flatMap(
            (group) =>
                group.slice(1),
        );
    }, [duplicateGroups]);


    /*
     * Media files can become large quickly.
     * We don't say they should be deleted.
     * We simply suggest reviewing them.
     */
    const largeMediaFiles = useMemo(() => {
        return files
            .filter((file) => {
                const category =
                    getFileCategory(
                        file.mime_type,
                    );

                return (
                    (
                        category === "video" ||
                        category === "audio"
                    ) &&
                    file.size >=
                    20 * 1024 * 1024
                );
            })
            .sort(
                (a, b) =>
                    b.size - a.size,
            );
    }, [files]);


    const suggestions =
        useMemo<Suggestion[]>(() => {
            const result: Suggestion[] = [];

            if (largeFiles.length > 0) {
                result.push({
                    type: "large",
                    title: "Large files",
                    description:
                        "These files are using a significant amount of your storage.",
                    files: largeFiles,
                    bytes: largeFiles.reduce(
                        (sum, file) =>
                            sum + file.size,
                        0,
                    ),
                });
            }

            if (duplicateFiles.length > 0) {
                result.push({
                    type: "duplicate",
                    title: "Duplicate files",
                    description:
                        "These files have the same SHA-256 content hash as another file.",
                    files: duplicateFiles,
                    bytes: duplicateFiles.reduce(
                        (sum, file) =>
                            sum + file.size,
                        0,
                    ),
                });
            }

            if (oldFiles.length > 0) {
                result.push({
                    type: "old",
                    title: "Older files",
                    description:
                        "These files were uploaded more than 180 days ago and may be worth reviewing.",
                    files: oldFiles,
                    bytes: oldFiles.reduce(
                        (sum, file) =>
                            sum + file.size,
                        0,
                    ),
                });
            }

            if (largeMediaFiles.length > 0) {
                result.push({
                    type: "media",
                    title: "Large media",
                    description:
                        "Large videos and audio files can consume storage quickly.",
                    files: largeMediaFiles,
                    bytes: largeMediaFiles.reduce(
                        (sum, file) =>
                            sum + file.size,
                        0,
                    ),
                });
            }

            return result;
        }, [
            largeFiles,
            duplicateFiles,
            oldFiles,
            largeMediaFiles,
        ]);


    const potentialSavings = useMemo(() => {
        /*
         * We intentionally do not simply add all
         * suggestion bytes because the same file
         * can appear in multiple categories.
         */
        const uniqueIds =
            new Set<string>();

        let total = 0;

        for (const suggestion of suggestions) {
            for (const file of suggestion.files) {
                if (
                    !uniqueIds.has(file.id)
                ) {
                    uniqueIds.add(
                        file.id,
                    );

                    total += file.size;
                }
            }
        }

        return total;
    }, [suggestions]);


    async function deleteFile(
        file: FileData,
    ) {
        const confirmed =
            window.confirm(
                `Delete "${file.name}"?\n\nThis action cannot be undone.`,
            );

        if (!confirmed) {
            return;
        }

        try {
            setDeletingId(file.id);

            await api.delete(
                `/api/files/${file.id}`,
            );

            setFiles((current) =>
                current.filter(
                    (item) =>
                        item.id !==
                        file.id,
                ),
            );

            setSelectedFiles(
                (current) => {
                    const next =
                        new Set(current);

                    next.delete(
                        file.id,
                    );

                    return next;
                },
            );

            if (
                selectedSuggestion
            ) {
                setSelectedSuggestion(
                    (current) =>
                        current
                            ? {
                                ...current,
                                files:
                                    current.files.filter(
                                        (item) =>
                                            item.id !==
                                            file.id,
                                    ),
                            }
                            : null,
                );
            }

        } catch (err: any) {
            setError(
                err.response?.data?.detail ||
                "Unable to delete file.",
            );

        } finally {
            setDeletingId(null);
        }
    }


    function toggleSelected(
        fileId: string,
    ) {
        setSelectedFiles(
            (current) => {
                const next =
                    new Set(current);

                if (
                    next.has(fileId)
                ) {
                    next.delete(fileId);
                } else {
                    next.add(fileId);
                }

                return next;
            },
        );
    }


    async function deleteSelected() {
        const filesToDelete =
            files.filter((file) =>
                selectedFiles.has(
                    file.id,
                ),
            );

        if (
            filesToDelete.length === 0
        ) {
            return;
        }

        const totalSize =
            filesToDelete.reduce(
                (sum, file) =>
                    sum + file.size,
                0,
            );

        const confirmed =
            window.confirm(
                `Delete ${filesToDelete.length} selected files and free approximately ${formatBytes(totalSize)}?`,
            );

        if (!confirmed) {
            return;
        }

        try {
            setDeletingId("bulk");

            await Promise.all(
                filesToDelete.map(
                    (file) =>
                        api.delete(
                            `/api/files/${file.id}`,
                        ),
                ),
            );

            const ids =
                new Set(
                    filesToDelete.map(
                        (file) =>
                            file.id,
                    ),
                );

            setFiles((current) =>
                current.filter(
                    (file) =>
                        !ids.has(
                            file.id,
                        ),
                ),
            );

            setSelectedFiles(
                new Set(),
            );

        } catch (err: any) {
            setError(
                err.response?.data?.detail ||
                "Unable to delete selected files.",
            );

        } finally {
            setDeletingId(null);
        }
    }


    if (loading) {
        return (
            <div className="dashboard-loading">
                Analyzing your storage...
            </div>
        );
    }


    return (
        <div className="cleanup-page">

            <header className="cleanup-header">

                <button
                    type="button"
                    className="cleanup-back"
                    onClick={() =>
                        navigate(
                            "/dashboard",
                        )
                    }
                >
                    <ArrowLeft size={18} />
                    Dashboard
                </button>

                <div className="cleanup-title-row">

                    <div>
                        <p className="cleanup-eyebrow">
                            Storage management
                        </p>

                        <h1>
                            Clean up storage
                        </h1>

                        <p>
                            Review files that may be
                            worth deleting. Nothing is
                            deleted automatically.
                        </p>
                    </div>

                    <div className="cleanup-storage-summary">

                        <HardDrive
                            size={20}
                        />

                        <div>
                            <strong>
                                {user
                                    ? formatBytes(
                                        user.storage_used,
                                    )
                                    : "—"}
                            </strong>

                            <span>
                                currently used
                            </span>
                        </div>

                    </div>

                </div>

            </header>


            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}


            <section className="cleanup-summary-grid">

                <div className="cleanup-stat-card">

                    <span>
                        Files
                    </span>

                    <strong>
                        {files.length}
                    </strong>

                    <p>
                        currently stored
                    </p>

                </div>


                <div className="cleanup-stat-card">

                    <span>
                        Review suggestions
                    </span>

                    <strong>
                        {suggestions.length}
                    </strong>

                    <p>
                        categories found
                    </p>

                </div>


                <div className="cleanup-stat-card highlight">

                    <span>
                        Potential space
                    </span>

                    <strong>
                        {formatBytes(
                            potentialSavings,
                        )}
                    </strong>

                    <p>
                        files worth reviewing
                    </p>

                </div>

            </section>


            {suggestions.length === 0 ? (

                <section className="cleanup-empty">

                    <div className="cleanup-empty-icon">
                        <CheckCircle2
                            size={34}
                        />
                    </div>

                    <h2>
                        Your storage looks good
                    </h2>

                    <p>
                        We couldn't find any obvious
                        files that need your attention.
                    </p>

                    <button
                        type="button"
                        className="primary-button"
                        onClick={() =>
                            navigate(
                                "/files",
                            )
                        }
                    >
                        View my files
                    </button>

                </section>

            ) : (

                <section className="cleanup-suggestions">

                    <div className="cleanup-section-heading">

                        <div>
                            <h2>
                                Review suggestions
                            </h2>

                            <p>
                                These are recommendations
                                based on your file metadata.
                                Review them before deleting
                                anything.
                            </p>
                        </div>

                    </div>


                    <div className="suggestion-grid">

                        {suggestions.map(
                            (suggestion) => (

                                <button
                                    type="button"
                                    key={
                                        suggestion.type
                                    }
                                    className="suggestion-card"
                                    onClick={() =>
                                        setSelectedSuggestion(
                                            suggestion,
                                        )
                                    }
                                >

                                    <div
                                        className={
                                            `suggestion-icon ${suggestion.type}`
                                        }
                                    >
                                        {suggestion.type ===
                                            "duplicate" ? (
                                            <Copy
                                                size={
                                                    22
                                                }
                                            />
                                        ) : suggestion.type ===
                                            "old" ? (
                                            <Calendar
                                                size={
                                                    22
                                                }
                                            />
                                        ) : (
                                            <AlertTriangle
                                                size={
                                                    22
                                                }
                                            />
                                        )}
                                    </div>


                                    <div className="suggestion-card-body">

                                        <h3>
                                            {
                                                suggestion.title
                                            }
                                        </h3>

                                        <p>
                                            {
                                                suggestion.description
                                            }
                                        </p>

                                        <div className="suggestion-meta">

                                            <span>
                                                {
                                                    suggestion
                                                        .files
                                                        .length
                                                }{" "}
                                                files
                                            </span>

                                            <strong>
                                                {formatBytes(
                                                    suggestion.bytes,
                                                )}
                                            </strong>

                                        </div>

                                    </div>

                                </button>

                            ),
                        )}

                    </div>

                </section>

            )}


            {selectedFiles.size > 0 && (

                <div className="cleanup-selection-bar">

                    <div>
                        <strong>
                            {selectedFiles.size} files
                            selected
                        </strong>

                        <span>
                            Review before deleting
                        </span>
                    </div>

                    <div>

                        <button
                            type="button"
                            className="secondary-button"
                            onClick={() =>
                                setSelectedFiles(
                                    new Set(),
                                )
                            }
                        >
                            Clear
                        </button>

                        <button
                            type="button"
                            className="danger-button"
                            disabled={
                                deletingId ===
                                "bulk"
                            }
                            onClick={
                                deleteSelected
                            }
                        >
                            <Trash2
                                size={17}
                            />

                            Delete selected
                        </button>

                    </div>

                </div>

            )}


            {selectedSuggestion && (

                <div
                    className="cleanup-modal-overlay"
                    onClick={() =>
                        setSelectedSuggestion(
                            null,
                        )
                    }
                >

                    <div
                        className="cleanup-modal"
                        onClick={(event) =>
                            event.stopPropagation()
                        }
                    >

                        <header className="cleanup-modal-header">

                            <div>

                                <span
                                    className={
                                        `modal-category ${selectedSuggestion.type}`
                                    }
                                >
                                    {selectedSuggestion.title}
                                </span>

                                <h2>
                                    Review files
                                </h2>

                                <p>
                                    Select individual
                                    files to delete, or
                                    close this window to
                                    leave them untouched.
                                </p>

                            </div>

                            <button
                                type="button"
                                className="icon-button"
                                onClick={() =>
                                    setSelectedSuggestion(
                                        null,
                                    )
                                }
                            >
                                <X size={20} />
                            </button>

                        </header>


                        <div className="cleanup-file-list">

                            {selectedSuggestion.files
                                .length === 0 ? (

                                <div className="cleanup-no-files">
                                    <CheckCircle2
                                        size={28}
                                    />

                                    <p>
                                        No files remain in
                                        this suggestion.
                                    </p>
                                </div>

                            ) : (

                                selectedSuggestion.files.map(
                                    (file) => (

                                        <div
                                            className="cleanup-file-row"
                                            key={
                                                file.id
                                            }
                                        >

                                            <button
                                                type="button"
                                                className={
                                                    `cleanup-checkbox ${selectedFiles.has(
                                                        file.id,
                                                    )
                                                        ? "checked"
                                                        : ""
                                                    }`
                                                }
                                                onClick={() =>
                                                    toggleSelected(
                                                        file.id,
                                                    )
                                                }
                                                aria-label={
                                                    `Select ${file.name}`
                                                }
                                            >
                                                {selectedFiles.has(
                                                    file.id,
                                                ) && (
                                                        <CheckCircle2
                                                            size={
                                                                17
                                                            }
                                                        />
                                                    )}
                                            </button>


                                            <div className="cleanup-file-icon">
                                                <FileTypeIcon
                                                    mimeType={
                                                        file.mime_type
                                                    }
                                                />
                                            </div>


                                            <div className="cleanup-file-info">

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


                                            <button
                                                type="button"
                                                className="cleanup-delete-button"
                                                disabled={
                                                    deletingId ===
                                                    file.id
                                                }
                                                onClick={() =>
                                                    deleteFile(
                                                        file,
                                                    )
                                                }
                                                title="Delete file"
                                            >
                                                <Trash2
                                                    size={
                                                        18
                                                    }
                                                />
                                            </button>

                                        </div>

                                    ),
                                )

                            )}

                        </div>


                        <footer className="cleanup-modal-footer">

                            <span>
                                {selectedSuggestion.files.length}{" "}
                                files ·{" "}
                                {formatBytes(
                                    selectedSuggestion.files.reduce(
                                        (
                                            sum,
                                            file,
                                        ) =>
                                            sum +
                                            file.size,
                                        0,
                                    ),
                                )}
                            </span>

                            <button
                                type="button"
                                className="secondary-button"
                                onClick={() =>
                                    setSelectedSuggestion(
                                        null,
                                    )
                                }
                            >
                                Done reviewing
                            </button>

                        </footer>

                    </div>

                </div>

            )}

        </div>
    );
}


export default Cleanup;
