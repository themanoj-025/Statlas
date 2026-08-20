export default function Loading() {
  return (
    <div
      className="container page"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "40vh",
      }}
    >
      <div
        className="spinner"
        role="status"
        aria-label="Loading"
        style={{
          width: 32,
          height: 32,
          border: "3px solid var(--color-border, #dce5e2)",
          borderTopColor: "var(--color-brand, #0f766e)",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
