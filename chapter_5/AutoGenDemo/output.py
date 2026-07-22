import streamlit as st
import requests
import time
from datetime import datetime

# ---------------------------- 页面配置 ----------------------------
st.set_page_config(
    page_title="BTC 价格看板",
    page_icon="₿",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------- 数据获取函数（安全取值 + 细化异常）---------------------------
def get_bitcoin_price():
    """从 CoinGecko 获取 BTC 当前价格和 24 小时变化，安全处理缺失字段并细化异常"""
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd",
        "include_24hr_change": "true",
    }

    for attempt in range(2):
        try:
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            btc = data.get("bitcoin", {})
            price = btc.get("usd")
            change_percent = btc.get("usd_24h_change")  # 可能为 None
            change_abs = None
            if price is not None and change_percent is not None:
                change_abs = price * change_percent / 100
            return price, change_percent, change_abs
        except requests.Timeout:
            raise RuntimeError("请求超时，请检查网络连接")
        except requests.HTTPError as e:
            status = e.response.status_code
            if status == 429:
                raise RuntimeError("API 请求过于频繁，请稍后重试")
            raise RuntimeError(f"API 返回错误 (状态码: {status})")
        except (KeyError, TypeError, ValueError) as e:
            raise RuntimeError(f"数据解析失败，返回结构可能已变更：{e}")
        except Exception as e:
            # 兜底其他未知异常
            raise RuntimeError(f"未知错误：{e}")

# ---------------------------- 会话状态初始化 ----------------------------
if "last_price" not in st.session_state:
    st.session_state.last_price = None
    st.session_state.last_change_percent = None
    st.session_state.last_change_abs = None
    st.session_state.last_updated = None
    st.session_state.error = None
    st.session_state.auto_refresh = False
    st.session_state.refresh_interval = 60

# ---------------------------- 侧边栏 ----------------------------
with st.sidebar:
    st.header("⚙️ 设置")
    # 自动刷新控制
    auto_refresh = st.checkbox(
        "🔄 自动刷新",
        value=st.session_state.auto_refresh,
        key="auto_refresh_checkbox"
    )
    st.session_state.auto_refresh = auto_refresh

    if auto_refresh:
        interval = st.slider(
            "刷新间隔（秒）",
            30, 120, st.session_state.refresh_interval,
            step=10,
            key="interval_slider"
        )
        st.session_state.refresh_interval = interval
        st.caption(f"将每 {interval} 秒自动刷新价格")
    else:
        st.caption("点击下方按钮手动刷新")

    st.divider()
    if st.button("🔁 立即刷新", use_container_width=True):
        # 清除错误提示并触发重跑
        st.session_state.error = None
        # 清除可能遗留的缓存（本次未使用缓存，保留将来扩展）
        st.cache_data.clear()
        st.rerun()

# ---------------------------- 自动刷新逻辑（非阻塞轮询）---------------------------
if st.session_state.auto_refresh:
    # 通过 rerun 循环实现无闪烁刷新
    time.sleep(st.session_state.refresh_interval)
    st.rerun()

# ---------------------------- 主界面 ----------------------------
st.title("₿ 比特币实时价格看板")
st.markdown("数据来源：CoinGecko（免费 API）")

# 获取数据
with st.spinner("获取最新价格中..."):
    try:
        price, change_percent, change_abs = get_bitcoin_price()
        st.session_state.last_price = price
        st.session_state.last_change_percent = change_percent
        st.session_state.last_change_abs = change_abs
        st.session_state.last_updated = datetime.now().strftime("%H:%M:%S")
        st.session_state.error = None
    except RuntimeError as e:
        st.session_state.error = f"❌ {e}"
        # 如果有旧数据，保留；否则设为 None
        if st.session_state.last_price is None:
            st.session_state.last_price = None

# 展示区域
error_msg = st.session_state.error
price = st.session_state.last_price
change_percent = st.session_state.last_change_percent
change_abs = st.session_state.last_change_abs
updated = st.session_state.last_updated

# 错误提示（区分是否有旧数据）
if error_msg:
    st.error(error_msg)
    if price is not None and updated:
        st.warning(f"⚠️ 显示的数据为上次成功获取的旧数据（于 {updated}）")
    elif price is None:
        st.info("当前无可用数据，请点击「立即刷新」按钮重试")

# 价格卡片（只有当 price 不为空时显示）
if price is not None:
    # 将涨跌幅作为 delta 显示在价格卡片上，节省空间
    delta_str = None
    if change_percent is not None:
        delta_str = f"{change_percent:+.2f}%"

    st.metric(
        label="💰 当前价格 (USD)",
        value=f"${price:,.2f}",
        delta=delta_str,
    )

    # 涨跌额单独显示为小文字
    if change_abs is not None:
        color = "green" if change_abs > 0 else "red" if change_abs < 0 else "gray"
        st.markdown(
            f"<span style='color:{color}; font-size:1.2rem;'>24h涨跌额：${change_abs:+,.2f}</span>",
            unsafe_allow_html=True,
        )
    else:
        st.caption("24h涨跌额：--")

    # 更新时间
    if updated:
        st.caption(f"🕒 数据更新于 {updated}")

elif not error_msg:
    # 既无数据也无错误，初始加载状态
    st.info("暂无数据，请点击「立即刷新」按钮获取最新行情。")

# ---------------------------- 页脚 ----------------------------
st.divider()
st.caption("⚠️ 数据仅供参考，不构成投资建议。API 可能存在延迟或因请求频率限制暂时不可用。")
