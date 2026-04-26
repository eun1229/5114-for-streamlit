import streamlit as st
import plotly.express as px


def render(query, start_date, end_date, route_filter):
    st.subheader("On time performance")
    st.caption(
        "% of times where a route stopped at a stop over 2.5 minutes early or 5 minutes late from their scheduled stop time. **Set the date range to a single date to view hourly performance.**"
    )

    single_day = start_date == end_date
    bucket_expr = "hour" if single_day else "trip_start_date"

    otp_df = query(f"""
        SELECT
            {bucket_expr} AS bucket,
            COUNT(*) AS event_count,
            AVG(CASE WHEN is_on_time THEN 1.0 ELSE 0 END) * 100 AS on_time_pct,
            AVG(CASE WHEN arrival_delay_seconds < -150 THEN 1.0 ELSE 0 END) * 100 AS early_pct,
            AVG(CASE WHEN arrival_delay_seconds > 300 THEN 1.0 ELSE 0 END) * 100 AS late_pct
        FROM LEMMING_DB.FINAL_PROJECT_MART.METRIC_ON_TIME
        WHERE trip_start_date BETWEEN '{start_date}' AND '{end_date}'
          AND route_name IN ('{route_filter}')
          AND is_on_time IS NOT NULL
          AND arrival_delay_seconds IS NOT NULL
          AND hour IS NOT NULL
        GROUP BY bucket
        ORDER BY bucket
    """)

    if otp_df.empty:
        st.info("No on-time performance data for selected filters.")
        return

    x_label = "Hour of day" if single_day else "Date"
    title = (
        f"Hourly on-time performance ({start_date})"
        if single_day
        else "Daily on-time performance"
    )
    hover_x = "%{x}:00" if single_day else "%{x|%Y-%m-%d}"

    fig = px.line(
        otp_df,
        x="BUCKET",
        y="ON_TIME_PCT",
        markers=True,
        title=title,
        labels={"BUCKET": x_label, "ON_TIME_PCT": "On-time %"},
        custom_data=["ON_TIME_PCT", "EARLY_PCT", "LATE_PCT", "EVENT_COUNT"],
        color_discrete_sequence=["#1a56db"],
    )
    fig.update_traces(
        hovertemplate=(
            f"<b>{hover_x}</b><br>"
            "On time: %{customdata[0]:.1f}%<br>"
            "Early: %{customdata[1]:.1f}%<br>"
            "Late: %{customdata[2]:.1f}%<br>"
            "Stop events: %{customdata[3]:,}"
            "<extra></extra>"
        )
    )
    fig.update_yaxes(range=[0, 100], ticksuffix="%")
    if single_day:
        fig.update_xaxes(
            tickmode="array",
            tickvals=list(range(24)),
            ticktext=[f"{h:02d}:00" for h in range(24)],
            range=[-0.5, 23.5],
        )
    else:
        fig.update_xaxes(tickformat="%Y-%m-%d", dtick="D1")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        "**Top 10 routes with lowest on-time performance**  \n"
        "<span style='color: gray; font-size: 0.875em;'>"
        "Ranked across all routes in the selected date range <b>Route filters will not affect this view</b>."
        "</span>",
        unsafe_allow_html=True,
    )

    worst_routes_df = query(f"""
        SELECT
            route_name,
            COUNT(*) AS event_count,
            AVG(CASE WHEN is_on_time THEN 1.0 ELSE 0 END) * 100 AS on_time_pct,
            AVG(CASE WHEN arrival_delay_seconds < -150 THEN 1.0 ELSE 0 END) * 100 AS early_pct,
            AVG(CASE WHEN arrival_delay_seconds > 300 THEN 1.0 ELSE 0 END) * 100 AS late_pct
        FROM LEMMING_DB.FINAL_PROJECT_MART.METRIC_ON_TIME
        WHERE trip_start_date BETWEEN '{start_date}' AND '{end_date}'
          AND is_on_time IS NOT NULL
          AND arrival_delay_seconds IS NOT NULL
          AND route_name IS NOT NULL
        GROUP BY route_name
        HAVING COUNT(*) >= 100
        ORDER BY on_time_pct ASC
        LIMIT 10
    """)

    if worst_routes_df.empty:
        st.info("No route-level on-time performance data for selected date range.")
    else:
        display_df = worst_routes_df.rename(columns={
            "ROUTE_NAME": "Route",
            "EVENT_COUNT": "# Data Points",
            "ON_TIME_PCT": "On-time %",
            "EARLY_PCT": "Early %",
            "LATE_PCT": "Late %",
        })[["Route", "# Data Points", "On-time %", "Early %", "Late %"]]
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "# Data Points": st.column_config.NumberColumn(format="%d"),
                "On-time %": st.column_config.NumberColumn(format="%.1f%%"),
                "Early %": st.column_config.NumberColumn(format="%.1f%%"),
                "Late %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )
