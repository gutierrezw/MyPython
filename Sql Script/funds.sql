SELECT * FROM bdinv.funds
-- where CIK = '0001051470'
;

SELECT id, fund_name, cik FROM funds WHERE fund_name LIKE '%VANGUARD%' LIMIT 10;

SELECT f.fund_name, ff.filing_date, ff.xml_url, ff.xml_local_path
FROM fund_filings ff 
JOIN funds f ON f.fund_id = ff.fund_id 
WHERE f.fund_id = 1
ORDER BY ff.filing_date DESC LIMIT 5;


DELETE FROM fund_holdings WHERE fund_id > 0;commit;
UPDATE funds SET cik = NULL WHERE id > 0;commit;