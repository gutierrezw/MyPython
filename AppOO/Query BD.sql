UPDATE bdinv.order_trader
SET status = 'Cancelled'
WHERE account = 'U4214563'
    AND status IN ('PreSubmitted', 'Submitted', 'New')
    AND orderType = 'STP LMT';