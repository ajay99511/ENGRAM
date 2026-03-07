import { useState, useEffect, useRef } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { chatStream } from "../lib/api";

export default function Spotlight() {
    const [query, setQuery] = useState("");
    const [answer, setAnswer] = useState("");
    const [loading, setLoading] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    // Make window transparent and handle blur
    useEffect(() => {
        document.body.style.background = "transparent";

        // Hide window when it loses focus (Raycast behavior)
        const handleBlur = () => {
            // Only hide if we aren't using dialogs (none here, so safe)
            getCurrentWindow().hide();
        };
        window.addEventListener("blur", handleBlur);

        return () => {
            document.body.style.background = "";
            window.removeEventListener("blur", handleBlur);
        };
    }, []);

    // auto focus when window is shown
    useEffect(() => {
        const handleFocus = () => {
            inputRef.current?.focus();
        };
        window.addEventListener("focus", handleFocus);
        // initial focus
        setTimeout(() => handleFocus(), 100);
        return () => window.removeEventListener("focus", handleFocus);
    }, []);

    // handle escape key to dismiss
    useEffect(() => {
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                getCurrentWindow().hide();
                // optionally clear query
                // setQuery(""); setAnswer(""); 
            }
        };
        window.addEventListener("keydown", handleKey);
        return () => window.removeEventListener("keydown", handleKey);
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim() || loading) return;

        setLoading(true);
        setAnswer("");
        try {
            for await (const chunk of chatStream(query, "smart")) {
                setAnswer((prev) => prev + chunk);
            }
        } catch (err) {
            setAnswer("Error: " + (err instanceof Error ? err.message : String(err)));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div
            style={{
                width: "100%",
                height: "100%",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                paddingTop: "60px", // space from top of window
            }}
        >
            <div
                className="spotlight-container"
                style={{
                    width: "100%",
                    maxWidth: 680,
                    background: "rgba(30, 30, 35, 0.75)",
                    backdropFilter: "blur(20px)",
                    WebkitBackdropFilter: "blur(20px)",
                    borderRadius: 16,
                    boxShadow: "0 10px 40px rgba(0,0,0,0.4)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                }}
            >
                <form
                    onSubmit={handleSubmit}
                    style={{ display: "flex", alignItems: "center", padding: "18px 24px" }}
                >
                    <span style={{ fontSize: 24, marginRight: 16 }}>✨</span>
                    <input
                        ref={inputRef}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Ask PersonalAssist anything..."
                        style={{
                            flex: 1,
                            background: "transparent",
                            border: "none",
                            outline: "none",
                            color: "white",
                            fontSize: 22,
                            fontFamily: "var(--font-sans)",
                        }}
                    />
                </form>

                {(answer || loading) && (
                    <div
                        style={{
                            borderTop: "1px solid rgba(255,255,255,0.08)",
                            padding: "20px 24px",
                            maxHeight: 280,
                            overflowY: "auto",
                            fontSize: 15,
                            lineHeight: 1.6,
                            color: "var(--text-secondary)",
                        }}
                    >
                        {loading && !answer ? (
                            <span className="spinner" style={{ marginRight: 8 }} />
                        ) : null}
                        <div style={{ whiteSpace: "pre-wrap" }}>{answer}</div>
                    </div>
                )}
            </div>
        </div>
    );
}
