import type { VictoryThemeDefinition } from "victory";

// We use CSS variables defined in index.css so the charts
// automatically adapt to dark/light mode without needing a React re-render.
// Note: SVG supports CSS variables natively for fill and stroke.

export const SynapseChartTheme: VictoryThemeDefinition = {
  area: {
    style: {
      data: {
        fill: "var(--primary)",
        fillOpacity: 0.2,
        stroke: "var(--primary)",
        strokeWidth: 2,
      },
    },
  },
  bar: {
    style: {
      data: {
        fill: "var(--primary)",
        padding: 8,
        strokeWidth: 0,
      },
      labels: {
        fill: "var(--foreground)",
        fontFamily: "Inter, sans-serif",
        fontSize: 12,
        padding: 8,
      },
    },
  },
  axis: {
    style: {
      axis: {
        fill: "transparent",
        stroke: "var(--border)",
        strokeWidth: 1,
        strokeLinecap: "round",
        strokeLinejoin: "round",
      },
      axisLabel: {
        textAnchor: "middle",
        fontFamily: "Inter, sans-serif",
        fontSize: 12,
        letterSpacing: "normal",
        padding: 8,
        fill: "var(--muted-foreground)",
      },
      grid: {
        fill: "none",
        stroke: "var(--border)",
        strokeDasharray: "4, 4",
        strokeLinecap: "round",
        strokeLinejoin: "round",
        pointerEvents: "painted",
      },
      ticks: {
        fill: "transparent",
        size: 5,
        stroke: "var(--border)",
        strokeWidth: 1,
        strokeLinecap: "round",
        strokeLinejoin: "round",
      },
      tickLabels: {
        fontFamily: "Inter, sans-serif",
        fontSize: 11,
        letterSpacing: "normal",
        padding: 8,
        fill: "var(--muted-foreground)",
      },
    },
  },
  chart: {
    padding: {
      top: 20,
      right: 20,
      bottom: 40,
      left: 50,
    },
  },
  tooltip: {
    style: {
      fill: "var(--popover-foreground)",
      fontFamily: "Inter, sans-serif",
      fontSize: 12,
    },
    flyoutStyle: {
      fill: "var(--popover)",
      stroke: "var(--border)",
      strokeWidth: 1,
      filter: "drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1))",
    },
    flyoutPadding: 8,
    pointerLength: 8,
  },
  voronoi: {
    style: {
      data: {
        fill: "transparent",
        stroke: "transparent",
        strokeWidth: 0,
      },
      labels: {
        fill: "var(--popover-foreground)",
        fontFamily: "Inter, sans-serif",
        fontSize: 12,
        padding: 8,
      },
      flyout: {
        fill: "var(--popover)",
        stroke: "var(--border)",
        strokeWidth: 1,
      },
    },
  },
  line: {
    style: {
      data: {
        fill: "transparent",
        stroke: "var(--primary)",
        strokeWidth: 2,
      },
    },
  },
  pie: {
    style: {
      data: {
        padding: 10,
        stroke: "var(--background)",
        strokeWidth: 2,
      },
      labels: {
        fill: "var(--foreground)",
        fontFamily: "Inter, sans-serif",
        fontSize: 12,
        padding: 20,
      },
    },
    colorScale: [
      "var(--primary)",
      "oklch(0.6 0.15 200)", // Muted blue
      "oklch(0.7 0.1 150)", // Sage green
      "oklch(0.6 0.15 30)",  // Warm orange
      "var(--muted)",
    ],
  },
};
