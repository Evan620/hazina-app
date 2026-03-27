-- Sample NSE and Ibuka companies for demo purposes
-- This file is used to seed the database for the prototype

-- Main NSE companies
INSERT INTO companies (symbol, name, sector, is_ibuka) VALUES
('SCOM', 'Safaricom PLC', 'Telecommunications', false),
('EQTY', 'Equity Group Holdings PLC', 'Banking', false),
('KCB', 'KCB Group PLC', 'Banking', false),
('COOP', 'Co-operative Bank of Kenya', 'Banking', false),
('ABSA', 'Absa Bank Kenya PLC', 'Banking', false),
('EABL', 'East African Breweries Limited', 'Manufacturing', false),
('BAT', 'British American Tobacco Kenya', 'Manufacturing', false),
('TKN', 'Telkom Kenya', 'Telecommunications', false),
('BAMB', 'Bamburi Cement PLC', 'Manufacturing', false),
('ARM', 'ARM Cement PLC', 'Manufacturing', false),
('NMG', 'Nation Media Group', 'Media', false),
('JUBH', 'Jubilee Holdings PLC', 'Insurance', false),
('CNTY', 'Centum Investment Company', 'Investment', false),
('KAPC', 'Kenya Airways PLC', 'Aviation', false),
('KENG', 'Kenya Electricity Generating Company', 'Energy', false),
('KNRE', 'Kenya Reinsurance Corporation', 'Insurance', false),
('BRCK', 'Brimstone Investment Company', 'Investment', false),
('LKL', 'Liberty Holdings Kenya', 'Insurance', false),
('SPWN', 'Spencer Flowers (Kenya) Ltd', 'Agriculture', false),
('WTKR', 'Walters (Kenya) Ltd', 'Investment', false)
ON CONFLICT (symbol) DO NOTHING;

-- Ibuka SME candidates
INSERT INTO companies (symbol, name, sector, is_ibuka) VALUES
('CPTY', 'Copy Cat Limited', 'Manufacturing', true),
('KKO', 'Koko Networks Kenya', 'Energy', true),
('MTB', 'Mastermind Tobacco Kenya', 'Manufacturing', true),
('ANDA', 'Andela Kenya', 'Technology', true),
('MNT', 'M-Kopa Solar', 'Energy', true),
('TWF', 'Twiga Foods', 'Agriculture', true),
('SFN', 'Sanergy', 'Waste Management', true),
('GRN', 'GreenPath Technologies', 'Construction', true),
('DLT', 'Dalbit Petroleum', 'Energy', true),
('LZ', 'LazyEye', 'Technology', true)
ON CONFLICT (symbol) DO NOTHING;
