from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.noc_ui import COLORS, kpi_card, page_header, render_grid, section_header, style_plotly


DATA_DIR = PROJECT_ROOT / "data"
ALARM_PATH = DATA_DIR / "alarm_logs.csv"
WINDOW_SIZE = pd.Timedelta(minutes=5)
WINDOW_STEP = pd.Timedelta(minutes=1)
UPDATE_SECONDS = 1
MAP_UPDATE_SECONDS = 8
CHART_BUCKETS = 10


@st.cache_data(ttl=600)
def load_processed_data(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path)
    data["alarm_raised_time"] = pd.to_datetime(
        data["alarm_raised_time"],
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
    )
    return data


def get_alarm_count_delta(
    alarms: pd.DataFrame, severity: str, now: pd.Timestamp
) -> tuple[int, int]:
    current_window_start = now - WINDOW_SIZE
    previous_window_start = now - (WINDOW_SIZE * 2)
    severity_match = alarms["severity"].astype(str).str.casefold() == severity.casefold()
    current_window = alarms["alarm_raised_time"].between(
        current_window_start, now, inclusive="both"
    )
    previous_window = alarms["alarm_raised_time"].between(
        previous_window_start, current_window_start, inclusive="left"
    )
    current_count = int((severity_match & current_window).sum())
    previous_count = int((severity_match & previous_window).sum())
    return current_count, current_count - previous_count


@st.cache_data
def get_sliding_window_ends(alarms: pd.DataFrame) -> pd.DatetimeIndex:
    alarm_times = alarms["alarm_raised_time"].dropna()
    if alarm_times.empty:
        return pd.DatetimeIndex([])
    return pd.date_range(
        alarm_times.min().floor("min"),
        alarm_times.max().floor("min"),
        freq=WINDOW_STEP,
    )


def build_total_alarm_chart(
    alarms: pd.DataFrame, current_time: pd.Timestamp
) -> go.Figure:
    current_minute = current_time.floor("min")
    chart_window_ends = pd.date_range(
        current_minute - (WINDOW_STEP * (CHART_BUCKETS - 1)),
        current_minute,
        freq=WINDOW_STEP,
    )
    severity_colors = {
        "Critical": COLORS["danger"],
        "Major": COLORS["warning"],
        "Minor": "#EAB308",
    }
    fig = go.Figure()
    for severity, color in severity_colors.items():
        values = []
        severity_rows = alarms["severity"].astype(str).str.casefold() == severity.casefold()
        for window_end in chart_window_ends:
            in_window = alarms["alarm_raised_time"].between(
                window_end - WINDOW_SIZE, window_end, inclusive="both"
            )
            values.append(int((severity_rows & in_window).sum()))
        fig.add_trace(
            go.Scatter(
                x=chart_window_ends,
                y=values,
                name=severity,
                mode="lines",
                line=dict(color=color, width=2),
                fill="tozeroy" if severity == "Critical" else None,
                fillcolor="rgba(239,68,68,.08)" if severity == "Critical" else None,
                hovertemplate=f"{severity}: %{{y}}<extra></extra>",
            )
        )
    fig.update_layout(
        title=dict(text="Real-time Alarm Timeline", font=dict(size=13, color=COLORS["text"])),
        xaxis_title=None,
        yaxis_title="Alarm count",
        hovermode="x unified",
    )
    return style_plotly(fig, height=355)


def build_alarm_map(alarms: pd.DataFrame, current_time: pd.Timestamp) -> go.Figure:
    window_start = current_time - WINDOW_SIZE
    points = alarms.loc[
        alarms["alarm_raised_time"].between(window_start, current_time, inclusive="both")
    ].dropna(subset=["latitude", "longitude"])
    color_map = {
        "Critical": COLORS["danger"],
        "Major": COLORS["warning"],
        "Minor": "#EAB308",
    }
    fig = go.Figure()
    for severity, group in points.groupby("severity"):
        fig.add_trace(
            go.Scattermap(
                lat=group["latitude"],
                lon=group["longitude"],
                mode="markers",
                name=str(severity),
                text=group["alarm_name"] + " · " + group["equipment_name"],
                marker=dict(
                    size=12,
                    color=color_map.get(str(severity), COLORS["primary"]),
                    opacity=0.82,
                ),
                hovertemplate="%{text}<extra></extra>",
            )
        )
    map_center = alarms.dropna(subset=["latitude", "longitude"])
    if not map_center.empty:
        center = {
            "lat": map_center["latitude"].mean(),
            "lon": map_center["longitude"].mean(),
        }
        fig.update_layout(map=dict(style="carto-darkmatter", center=center, zoom=12))
    fig.update_layout(
        title=dict(text="Network Alarm Heat Map", font=dict(size=13)),
        uirevision="live-alarm-map",
    )
    return style_plotly(fig, height=355)


df = load_processed_data(ALARM_PATH)
page_header(
    "Network Overview",
    "Real-time network operations, alarm velocity, and regional service health.",
    "Telecom NOC Command Center",
)

tabs = st.tabs(["Operations Overview", "Live Alarm Explorer"])

with tabs[1]:
    section_header("Live Alarm Stream", f"{len(df):,} records")
    render_grid(
        df.sort_values("alarm_raised_time", ascending=False),
        key="alarm_log_grid",
        height=610,
        search_label="Search alarms",
    )

with tabs[0]:
    live_mode = st.sidebar.toggle("Live simulation", value=True)
    window_ends = get_sliding_window_ends(df)
    if "sim_index" not in st.session_state:
        st.session_state.sim_index = 0

    kpi_slots = st.columns(5)
    critical_slot = kpi_slots[0].empty()
    major_slot = kpi_slots[1].empty()
    minor_slot = kpi_slots[2].empty()
    active_slot = kpi_slots[3].empty()
    sla_slot = kpi_slots[4].empty()

    chart_col, map_col = st.columns([1.08, 0.92])
    with chart_col:
        with st.container(border=True):
            chart_panel = st.empty()
    with map_col:
        with st.container(border=True):
            map_panel = st.empty()

    if window_ends.empty:
        with critical_slot:
            kpi_card("Critical alarms", 0, "No valid timestamps", "danger", "!")
        with major_slot:
            kpi_card("Major alarms", 0, "No valid timestamps", "warning", "▲")
        with minor_slot:
            kpi_card("Minor alarms", 0, "No valid timestamps", "warning", "•")
        with active_slot:
            kpi_card("Active incidents", 0, "Current 5-minute window", "primary", "⌁")
        with sla_slot:
            kpi_card("SLA risk", "Low", "No active alarm window", "success", "✓")
        chart_panel.info("No valid alarm timestamps available.")
        map_panel.info("No valid alarm locations available.")
    else:
        @st.fragment(run_every=UPDATE_SECONDS if live_mode else None)
        def render_live_simulation(
            data: pd.DataFrame, windows: pd.DatetimeIndex, is_live: bool
        ) -> None:
            if is_live:
                st.session_state.sim_index = (
                    st.session_state.sim_index + 1
                ) % len(windows)
            idx = st.session_state.sim_index if is_live else -1
            current_time = windows[idx]

            counts = {}
            for severity in ("Critical", "Major", "Minor"):
                counts[severity] = get_alarm_count_delta(data, severity, current_time)
            active_count = sum(value[0] for value in counts.values())
            sla_risk = "High" if counts["Critical"][0] else "Guarded"

            cards = [
                (critical_slot, "Critical alarms", counts["Critical"], "danger", "!"),
                (major_slot, "Major alarms", counts["Major"], "warning", "▲"),
                (minor_slot, "Minor alarms", counts["Minor"], "warning", "•"),
            ]
            for slot, label, (value, delta), tone, icon in cards:
                with slot:
                    direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
                    kpi_card(
                        label,
                        value,
                        f"{abs(delta)} {direction} vs previous window",
                        tone,
                        icon,
                        positive=delta <= 0,
                    )
            with active_slot:
                kpi_card(
                    "Active incidents",
                    active_count,
                    current_time.strftime("Window ending %H:%M"),
                    "primary",
                    "⌁",
                )
            with sla_slot:
                kpi_card(
                    "SLA risk",
                    sla_risk,
                    "Derived from critical load",
                    "danger" if sla_risk == "High" else "success",
                    "◆",
                    positive=sla_risk != "High",
                )

            with chart_panel:
                st.plotly_chart(
                    build_total_alarm_chart(data, current_time),
                    width="stretch",
                    config={"displayModeBar": False, "responsive": True},
                )
        render_live_simulation(df, window_ends, live_mode)

        @st.fragment(run_every=MAP_UPDATE_SECONDS if live_mode else None)
        def render_live_map(
            data: pd.DataFrame, windows: pd.DatetimeIndex, is_live: bool
        ) -> None:
            idx = st.session_state.sim_index if is_live else -1
            current_time = windows[idx]
            points = data.loc[
                data["alarm_raised_time"].between(
                    current_time - WINDOW_SIZE, current_time, inclusive="both"
                )
            ].dropna(subset=["latitude", "longitude"])

            with map_panel:
                if points.empty:
                    st.info("No alarm locations in the current window.")
                else:
                    st.plotly_chart(
                        build_alarm_map(data, current_time),
                        width="stretch",
                        config={
                            "displayModeBar": False,
                            "responsive": True,
                            "scrollZoom": False,
                        },
                        key="live_alarm_map",
                    )

        render_live_map(df, window_ends, live_mode)
