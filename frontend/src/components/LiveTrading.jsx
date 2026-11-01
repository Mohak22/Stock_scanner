import { useEffect, useState } from 'react'
import './LiveTrading.css'

const API_BASE = 'http://127.0.0.1:8000'

function LiveTrading() {
    const [status, setStatus] = useState(null)
    const [profile, setProfile] = useState(null)

    const [instruments, setInstruments] = useState(
        'NSE:INFY,NSE:TCS'
    )

    const [ltpData, setLtpData] = useState(null)

    const [orders, setOrders] = useState(null)
    const [positions, setPositions] = useState(null)
    const [holdings, setHoldings] = useState(null)

    const [strategySlug, setStrategySlug] = useState('')
    const [strategyVersion, setStrategyVersion] =
        useState('1')

    const [orderForm, setOrderForm] = useState({
        signal_id: '',
        tradingsymbol: '',
        transaction_type: 'BUY',
        quantity: 1,
        order_type: 'MARKET',
        product: 'CNC',
        price: '',
        validity: 'DAY',
        market_protection: -1,
        confirm_live: false,
        notes: '',
    })

    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState(null)
    const [executionResult, setExecutionResult] =
        useState(null)

    async function apiRequest(
        path,
        options = {}
    ) {
        const response = await fetch(
            `${API_BASE}${path}`,
            {
                ...options,
                headers: {
                    'Content-Type':
                        'application/json',
                    ...(options.headers || {}),
                },
            }
        )

        const data = await response.json()

        if (!response.ok) {
            throw new Error(
                data.detail ||
                    data.message ||
                    'Request failed.'
            )
        }

        return data
    }

    async function connectZerodha() {
        try {
            const data = await apiRequest(
                '/execution/login-url'
            )

            window.open(
                data.login_url,
                '_blank',
                'noopener,noreferrer'
            )
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.message,
            })
        }
    }

    async function loadProfile() {
        setLoading(true)
        setMessage(null)

        try {
            const data = await apiRequest(
                '/execution/profile'
            )

            setProfile(data)
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.message,
            })
        } finally {
            setLoading(false)
        }
    }

    async function fetchLtp() {
        setLoading(true)
        setMessage(null)

        try {
            const data = await apiRequest(
                `/execution/ltp?instruments=${encodeURIComponent(
                    instruments
                )}`
            )

            setLtpData(data)
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.message,
            })
        } finally {
            setLoading(false)
        }
    }

    async function loadOrders() {
        setLoading(true)
        setMessage(null)

        try {
            const data = await apiRequest(
                '/execution/orders'
            )

            setOrders(data)
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.message,
            })
        } finally {
            setLoading(false)
        }
    }

    async function loadPositions() {
        setLoading(true)
        setMessage(null)

        try {
            const data = await apiRequest(
                '/execution/positions'
            )

            setPositions(data)
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.message,
            })
        } finally {
            setLoading(false)
        }
    }

    async function loadHoldings() {
        setLoading(true)
        setMessage(null)

        try {
            const data = await apiRequest(
                '/execution/holdings'
            )

            setHoldings(data)
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.message,
            })
        } finally {
            setLoading(false)
        }
    }

    function updateOrderField(
        field,
        value
    ) {
        setOrderForm((current) => ({
            ...current,
            [field]: value,
        }))
    }

    async function submitOrder(event) {
        event.preventDefault()

        setLoading(true)
        setMessage(null)
        setExecutionResult(null)

        if (!strategySlug.trim()) {
            setMessage({
                type: 'error',
                text:
                    'Enter the locked strategy slug.',
            })

            setLoading(false)
            return
        }

        const payload = {
            signal_id:
                orderForm.signal_id.trim(),
            tradingsymbol:
                orderForm.tradingsymbol.trim(),
            transaction_type:
                orderForm.transaction_type,
            quantity: Number(
                orderForm.quantity
            ),
            order_type:
                orderForm.order_type,
            product:
                orderForm.product,
            validity:
                orderForm.validity,
            market_protection:
                Number(
                    orderForm.market_protection
                ),
            confirm_live:
                orderForm.confirm_live,
            notes:
                orderForm.notes.trim() || null,
        }

        if (
            orderForm.order_type ===
            'LIMIT'
        ) {
            payload.price = Number(
                orderForm.price
            )
        }

        try {
            const data = await apiRequest(
                `/execution/strategies/${encodeURIComponent(
                    strategySlug.trim()
                )}/v${Number(
                    strategyVersion
                )}/order`,
                {
                    method: 'POST',
                    body: JSON.stringify(
                        payload
                    ),
                }
            )

            setExecutionResult(data)

            setMessage({
                type: 'success',
                text:
                    data.mode === 'paper'
                        ? 'Paper order created successfully.'
                        : 'Order submitted to Zerodha.',
            })
        } catch (error) {
            setMessage({
                type: 'error',
                text: error.message,
            })
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        let isMounted = true

        async function fetchInitialStatus() {
            try {
                const response = await fetch(
                    `${API_BASE}/execution/status`
                )

                const data = await response.json()

                if (!response.ok) {
                    throw new Error(
                        data.detail ||
                        data.message ||
                        'Failed to load execution status.'
                    )
                }

                if (isMounted) {
                    setStatus(data)
                }
            } catch (error) {
                if (isMounted) {
                    setMessage({
                        type: 'error',
                        text: error.message,
                    })
                }
            }
        }

        fetchInitialStatus()

        return () => {
            isMounted = false
        }
    }, [])

    return (
        <div className="live-trading">

            <div className="live-trading-header">

                <div>
                    <span className="live-trading-kicker">
                        EXECUTION WORKSPACE
                    </span>

                    <h1>
                        Live Trading
                    </h1>

                    <p>
                        Connect Zerodha, inspect
                        market state and execute
                        orders from locked strategies.
                    </p>
                </div>

                <div
                    className={`execution-mode-badge ${
                        status?.execution_mode ===
                        'live'
                            ? 'live'
                            : 'paper'
                    }`}
                >
                    <span></span>

                    {status?.execution_mode
                        ?.toUpperCase() ||
                        'LOADING'}
                </div>

            </div>

            {message && (
                <div
                    className={`execution-message ${message.type}`}
                >
                    {message.text}
                </div>
            )}

            <section className="execution-section">

                <div className="execution-section-header">

                    <div>
                        <span>
                            CONNECTION
                        </span>

                        <h2>
                            Zerodha Gateway
                        </h2>
                    </div>

                    <button
                        className="execution-primary-button"
                        onClick={
                            connectZerodha
                        }
                    >
                        Connect Zerodha
                    </button>

                </div>

                <div className="connection-grid">

                    <div className="connection-card">

                        <span>
                            API KEY
                        </span>

                        <strong>
                            {status
                                ?.zerodha_api_key_configured
                                ? 'CONFIGURED'
                                : 'NOT CONFIGURED'}
                        </strong>

                    </div>

                    <div className="connection-card">

                        <span>
                            ACCESS TOKEN
                        </span>

                        <strong>
                            {status
                                ?.zerodha_access_token_configured
                                ? 'CONFIGURED'
                                : 'NOT CONFIGURED'}
                        </strong>

                    </div>

                    <div className="connection-card">

                        <span>
                            EXECUTION MODE
                        </span>

                        <strong>
                            {status?.execution_mode?.toUpperCase() ||
                                'UNKNOWN'}
                        </strong>

                    </div>

                    <div className="connection-card">

                        <span>
                            ACCOUNT
                        </span>

                        <strong>
                            {profile?.data?.user_name ||
                                profile?.data?.user_id ||
                                'Not connected'}
                        </strong>

                    </div>

                </div>

                <div className="connection-actions">

                    <button
                        className="execution-secondary-button"
                        onClick={
                            loadProfile
                        }
                        disabled={loading}
                    >
                        Check Connection
                    </button>

                </div>

            </section>

            <section className="execution-section">

                <div className="execution-section-header">

                    <div>
                        <span>
                            MARKET DATA
                        </span>

                        <h2>
                            Live Prices
                        </h2>
                    </div>

                </div>

                <div className="market-data-controls">

                    <input
                        value={instruments}
                        onChange={(event) =>
                            setInstruments(
                                event.target.value
                            )
                        }
                        placeholder="NSE:INFY,NSE:TCS"
                    />

                    <button
                        className="execution-secondary-button"
                        onClick={fetchLtp}
                        disabled={loading}
                    >
                        Fetch LTP
                    </button>

                </div>

                {ltpData && (
                    <div className="json-panel">
                        <pre>
                            {JSON.stringify(
                                ltpData,
                                null,
                                2
                            )}
                        </pre>
                    </div>
                )}

            </section>

            <section className="execution-section">

                <div className="execution-section-header">

                    <div>
                        <span>
                            ACCOUNT STATE
                        </span>

                        <h2>
                            Portfolio & Orders
                        </h2>
                    </div>

                </div>

                <div className="account-action-grid">

                    <button
                        onClick={loadOrders}
                        disabled={loading}
                    >
                        Orders
                    </button>

                    <button
                        onClick={loadPositions}
                        disabled={loading}
                    >
                        Positions
                    </button>

                    <button
                        onClick={loadHoldings}
                        disabled={loading}
                    >
                        Holdings
                    </button>

                </div>

                {orders && (
                    <div className="data-panel">

                        <div className="data-panel-header">
                            Orders
                        </div>

                        <pre>
                            {JSON.stringify(
                                orders,
                                null,
                                2
                            )}
                        </pre>

                    </div>
                )}

                {positions && (
                    <div className="data-panel">

                        <div className="data-panel-header">
                            Positions
                        </div>

                        <pre>
                            {JSON.stringify(
                                positions,
                                null,
                                2
                            )}
                        </pre>

                    </div>
                )}

                {holdings && (
                    <div className="data-panel">

                        <div className="data-panel-header">
                            Holdings
                        </div>

                        <pre>
                            {JSON.stringify(
                                holdings,
                                null,
                                2
                            )}
                        </pre>

                    </div>
                )}

            </section>

            <section className="execution-section order-section">

                <div className="execution-section-header">

                    <div>
                        <span>
                            STRATEGY EXECUTION
                        </span>

                        <h2>
                            Submit Order
                        </h2>

                        <p>
                            Orders are accepted only
                            from LOCKED strategies.
                        </p>
                    </div>

                </div>

                <form
                    className="execution-form"
                    onSubmit={submitOrder}
                >

                    <div className="execution-form-grid">

                        <div className="execution-field wide">

                            <label>
                                Strategy Slug
                            </label>

                            <input
                                value={
                                    strategySlug
                                }
                                onChange={(event) =>
                                    setStrategySlug(
                                        event.target.value
                                    )
                                }
                                placeholder="strategy-slug"
                            />

                        </div>

                        <div className="execution-field">

                            <label>
                                Version
                            </label>

                            <input
                                type="number"
                                min="1"
                                value={
                                    strategyVersion
                                }
                                onChange={(event) =>
                                    setStrategyVersion(
                                        event.target.value
                                    )
                                }
                            />

                        </div>

                        <div className="execution-field">

                            <label>
                                Signal ID
                            </label>

                            <input
                                value={
                                    orderForm.signal_id
                                }
                                onChange={(event) =>
                                    updateOrderField(
                                        'signal_id',
                                        event.target.value
                                    )
                                }
                                placeholder="signal-001"
                                required
                            />

                        </div>

                        <div className="execution-field">

                            <label>
                                Trading Symbol
                            </label>

                            <input
                                value={
                                    orderForm.tradingsymbol
                                }
                                onChange={(event) =>
                                    updateOrderField(
                                        'tradingsymbol',
                                        event.target.value
                                    )
                                }
                                placeholder="INFY"
                                required
                            />

                        </div>

                        <div className="execution-field">

                            <label>
                                Side
                            </label>

                            <select
                                value={
                                    orderForm.transaction_type
                                }
                                onChange={(event) =>
                                    updateOrderField(
                                        'transaction_type',
                                        event.target.value
                                    )
                                }
                            >
                                <option value="BUY">
                                    BUY
                                </option>

                                <option value="SELL">
                                    SELL
                                </option>
                            </select>

                        </div>

                        <div className="execution-field">

                            <label>
                                Quantity
                            </label>

                            <input
                                type="number"
                                min="1"
                                value={
                                    orderForm.quantity
                                }
                                onChange={(event) =>
                                    updateOrderField(
                                        'quantity',
                                        event.target.value
                                    )
                                }
                            />

                        </div>

                        <div className="execution-field">

                            <label>
                                Order Type
                            </label>

                            <select
                                value={
                                    orderForm.order_type
                                }
                                onChange={(event) =>
                                    updateOrderField(
                                        'order_type',
                                        event.target.value
                                    )
                                }
                            >
                                <option value="MARKET">
                                    MARKET
                                </option>

                                <option value="LIMIT">
                                    LIMIT
                                </option>
                            </select>

                        </div>

                        {orderForm.order_type ===
                            'LIMIT' && (
                            <div className="execution-field">

                                <label>
                                    Limit Price
                                </label>

                                <input
                                    type="number"
                                    min="0.01"
                                    step="0.01"
                                    value={
                                        orderForm.price
                                    }
                                    onChange={(event) =>
                                        updateOrderField(
                                            'price',
                                            event.target.value
                                        )
                                    }
                                    required
                                />

                            </div>
                        )}

                        <div className="execution-field">

                            <label>
                                Product
                            </label>

                            <select
                                value={
                                    orderForm.product
                                }
                                onChange={(event) =>
                                    updateOrderField(
                                        'product',
                                        event.target.value
                                    )
                                }
                            >
                                <option value="CNC">
                                    CNC
                                </option>

                                <option value="MIS">
                                    MIS
                                </option>
                            </select>

                        </div>

                        <div className="execution-field">

                            <label>
                                Validity
                            </label>

                            <select
                                value={
                                    orderForm.validity
                                }
                                onChange={(event) =>
                                    updateOrderField(
                                        'validity',
                                        event.target.value
                                    )
                                }
                            >
                                <option value="DAY">
                                    DAY
                                </option>

                                <option value="IOC">
                                    IOC
                                </option>
                            </select>

                        </div>

                        <div className="execution-field wide">

                            <label>
                                Notes
                            </label>

                            <input
                                value={
                                    orderForm.notes
                                }
                                onChange={(event) =>
                                    updateOrderField(
                                        'notes',
                                        event.target.value
                                    )
                                }
                                placeholder="Optional execution note"
                            />

                        </div>

                    </div>

                    <div className="execution-warning">

                        <strong>
                            Execution control
                        </strong>

                        <span>
                            Paper mode creates an audit
                            record without sending an
                            order to Zerodha. Live mode
                            additionally requires explicit
                            confirmation.
                        </span>

                    </div>

                    {status?.execution_mode ===
                        'live' && (
                        <label className="live-confirmation">

                            <input
                                type="checkbox"
                                checked={
                                    orderForm.confirm_live
                                }
                                onChange={(event) =>
                                    updateOrderField(
                                        'confirm_live',
                                        event.target.checked
                                    )
                                }
                            />

                            <span>
                                I explicitly confirm
                                this live order.
                            </span>

                        </label>
                    )}

                    <div className="execution-submit-row">

                        <button
                            type="submit"
                            className="execution-primary-button submit-order-button"
                            disabled={loading}
                        >
                            {loading
                                ? 'PROCESSING...'
                                : status?.execution_mode ===
                                    'live'
                                  ? 'SUBMIT LIVE ORDER'
                                  : 'CREATE PAPER ORDER'}
                        </button>

                    </div>

                </form>

            </section>

            {executionResult && (
                <section className="execution-section">

                    <div className="execution-section-header">

                        <div>
                            <span>
                                EXECUTION RESULT
                            </span>

                            <h2>
                                Order Audit
                            </h2>
                        </div>

                    </div>

                    <div className="execution-result-grid">

                        <div>
                            <span>
                                EXECUTION ID
                            </span>

                            <strong>
                                {
                                    executionResult.execution_id
                                }
                            </strong>
                        </div>

                        <div>
                            <span>
                                STATUS
                            </span>

                            <strong>
                                {
                                    executionResult.status
                                }
                            </strong>
                        </div>

                        <div>
                            <span>
                                MODE
                            </span>

                            <strong>
                                {
                                    executionResult.mode
                                }
                            </strong>
                        </div>

                        <div>
                            <span>
                                ORDER ID
                            </span>

                            <strong>
                                {
                                    executionResult
                                        .zerodha_order_id ||
                                    executionResult
                                        .paper_order_id ||
                                    '—'
                                }
                            </strong>
                        </div>

                    </div>

                    <div className="json-panel">
                        <pre>
                            {JSON.stringify(
                                executionResult,
                                null,
                                2
                            )}
                        </pre>
                    </div>

                </section>
            )}

        </div>
    )
}

export default LiveTrading