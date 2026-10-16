import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

// A small pixel-grid mark (four blocks, two colors) echoing the site's
// light-retro styling and its two accent hues - not a photo, so it reads
// fine at favicon size.
export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          background: "#15131f",
          borderRadius: 7,
        }}
      >
        <div style={{ display: "flex", flexWrap: "wrap", width: "100%", height: "100%", padding: 5 }}>
          <div style={{ width: "50%", height: "50%", background: "#7c6cf0" }} />
          <div style={{ width: "50%", height: "50%", background: "#eab06a" }} />
          <div style={{ width: "50%", height: "50%", background: "#eab06a" }} />
          <div style={{ width: "50%", height: "50%", background: "#7c6cf0" }} />
        </div>
      </div>
    ),
    { ...size },
  );
}
