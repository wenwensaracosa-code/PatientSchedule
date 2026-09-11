<?php
// ========================================================
// eDoc Doctor Appointment System - Database Connection
// Supports Supabase (PostgreSQL via PDO) and MySQL (via mysqli/PDO)
// Automatically loads .env configuration if present
// ========================================================

// 1. Serverless Session Storage Setup
if (session_status() === PHP_SESSION_NONE) {
    $currentSavePath = ini_get('session.save_path');
    if (empty($currentSavePath) || !is_writable($currentSavePath)) {
        if (is_dir('/tmp') && is_writable('/tmp')) {
            @ini_set('session.save_path', '/tmp');
        }
    }
}

// 2. Load .env file (for local development or custom deployments)
if (!function_exists('edoc_load_env')) {
    function edoc_load_env($filePath) {
        if (!file_exists($filePath) || !is_readable($filePath)) {
            return;
        }
        $lines = file($filePath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        foreach ($lines as $line) {
            $line = trim($line);
            if ($line === '' || strpos($line, '#') === 0) {
                continue;
            }
            if (strpos($line, '=') !== false) {
                list($name, $value) = explode('=', $line, 2);
                $name = trim($name);
                $value = trim($value);
                // Remove wrapping quotes if present
                if ((strpos($value, '"') === 0 && substr($value, -1) === '"') ||
                    (strpos($value, "'") === 0 && substr($value, -1) === "'")) {
                    $value = substr($value, 1, -1);
                }
                if (!array_key_exists($name, $_SERVER) && !array_key_exists($name, $_ENV) && getenv($name) === false) {
                    putenv("{$name}={$value}");
                    $_ENV[$name] = $value;
                    $_SERVER[$name] = $value;
                }
            }
        }
    }
}

// Check for .env in current and parent directories
$envPaths = [
    __DIR__ . '/.env',
    __DIR__ . '/../.env',
    __DIR__ . '/.env.local',
    __DIR__ . '/../.env.local'
];
foreach ($envPaths as $p) {
    edoc_load_env($p);
}

// Helper to retrieve configuration value
if (!function_exists('edoc_get_env')) {
    function edoc_get_env($key, $default = null) {
        $val = getenv($key);
        if ($val !== false && $val !== '') {
            return $val;
        }
        if (isset($_ENV[$key]) && $_ENV[$key] !== '') {
            return $_ENV[$key];
        }
        if (isset($_SERVER[$key]) && $_SERVER[$key] !== '') {
            return $_SERVER[$key];
        }
        return $default;
    }
}

// 3. Resolve Database Configuration
$databaseUrl = edoc_get_env('DATABASE_URL', edoc_get_env('SUPABASE_DB_URL'));
$dbType = null;
$host = null;
$port = null;
$user = null;
$pass = null;
$dbname = null;
$sslmode = edoc_get_env('DB_SSLMODE', 'require');

if (!empty($databaseUrl)) {
    $parsed = parse_url($databaseUrl);
    if ($parsed) {
        $scheme = strtolower($parsed['scheme'] ?? '');
        if (strpos($scheme, 'postgres') !== false || strpos($scheme, 'pgsql') !== false) {
            $dbType = 'pgsql';
        } elseif (strpos($scheme, 'mysql') !== false) {
            $dbType = 'mysql';
        }
        $host = $parsed['host'] ?? null;
        $port = isset($parsed['port']) ? (int)$parsed['port'] : null;
        $user = isset($parsed['user']) ? urldecode($parsed['user']) : null;
        $pass = isset($parsed['pass']) ? urldecode($parsed['pass']) : '';
        $dbname = isset($parsed['path']) ? ltrim($parsed['path'], '/') : null;
        if (isset($parsed['query'])) {
            parse_str($parsed['query'], $queryParams);
            if (isset($queryParams['sslmode'])) {
                $sslmode = $queryParams['sslmode'];
            }
        }
    }
}

// Fallback to individual variables if not parsed from URL
$defaultSupabaseHost = 'aws-0-ap-southeast-2.pooler.supabase.com';
$defaultSupabasePort = 6543;
$defaultSupabaseUser = 'postgres.lmakqewnzicneuxndanw';
$defaultSupabasePass = 'Buenavidez.890';
$defaultSupabaseDb   = 'postgres';

if (empty($host)) {
    $host = edoc_get_env('DB_HOST', edoc_get_env('SUPABASE_DB_HOST', edoc_get_env('MYSQL_HOST', $defaultSupabaseHost)));
}
if (empty($port)) {
    $port = edoc_get_env('DB_PORT', edoc_get_env('SUPABASE_DB_PORT', edoc_get_env('MYSQL_PORT', ($host === 'localhost' ? 3306 : $defaultSupabasePort))));
}
if (empty($user)) {
    $user = edoc_get_env('DB_USER', edoc_get_env('SUPABASE_DB_USER', edoc_get_env('MYSQL_USER', $defaultSupabaseUser)));
}
if ($pass === null || $pass === '') {
    $pass = edoc_get_env('DB_PASSWORD', edoc_get_env('SUPABASE_DB_PASSWORD', edoc_get_env('MYSQL_PASSWORD', $defaultSupabasePass)));
}
if (empty($dbname)) {
    $dbname = edoc_get_env('DB_NAME', edoc_get_env('SUPABASE_DB_NAME', edoc_get_env('MYSQL_DATABASE', $defaultSupabaseDb)));
}

// Auto-detect Database Type if not specified
if (empty($dbType)) {
    $explicitType = strtolower((string)edoc_get_env('DB_TYPE', ''));
    if ($explicitType === 'pgsql' || $explicitType === 'postgres' || $explicitType === 'postgresql') {
        $dbType = 'pgsql';
    } elseif ($explicitType === 'mysql') {
        $dbType = 'mysql';
    } elseif (
        strpos((string)$host, 'supabase.co') !== false ||
        strpos((string)$host, 'supabase.com') !== false ||
        (int)$port === 5432 ||
        (int)$port === 6543
    ) {
        $dbType = 'pgsql';
    } elseif ($host === 'localhost') {
        $dbType = 'mysql';
    } else {
        $dbType = 'pgsql';
    }
}

// Set standard default ports
if (empty($port)) {
    $port = ($dbType === 'pgsql') ? 5432 : 3306;
}

// 4. PDO MySQLi Compatibility Adapter Classes
if (!class_exists('PDOResultWrapper')) {
    class PDOResultWrapper {
        private $rows = [];
        private $cursor = 0;
        public $num_rows = 0;

        public function __construct(array $rows) {
            $this->rows = $rows;
            $this->num_rows = count($rows);
            $this->cursor = 0;
        }

        public function fetch_assoc() {
            if ($this->cursor < $this->num_rows) {
                return $this->rows[$this->cursor++];
            }
            return null;
        }

        public function fetch_array($mode = 3) {
            // 1 = MYSQLI_NUM, 2 = MYSQLI_ASSOC, 3 = MYSQLI_BOTH
            if ($this->cursor < $this->num_rows) {
                $row = $this->rows[$this->cursor++];
                if ($mode === 2) {
                    return $row;
                }
                if ($mode === 1) {
                    return array_values($row);
                }
                return array_merge(array_values($row), $row);
            }
            return null;
        }

        public function fetch_all($mode = 1) {
            if ($mode === 2) {
                return $this->rows;
            }
            $result = [];
            foreach ($this->rows as $r) {
                $result[] = ($mode === 1) ? array_values($r) : $r;
            }
            return $result;
        }

        public function data_seek($offset) {
            if ($offset >= 0 && $offset < $this->num_rows) {
                $this->cursor = $offset;
                return true;
            }
            return false;
        }

        public function free() {
            $this->rows = [];
            $this->num_rows = 0;
            $this->cursor = 0;
        }

        public function close() {
            $this->free();
        }
    }
}

if (!class_exists('PDOStatementWrapper')) {
    class PDOStatementWrapper {
        private $pdoStmt;
        private $params = [];
        public $error = '';

        public function __construct(PDOStatement $pdoStmt) {
            $this->pdoStmt = $pdoStmt;
        }

        public function bind_param($types, &...$params) {
            $this->params = [];
            foreach ($params as $key => &$param) {
                $this->params[] = &$param;
            }
            return true;
        }

        public function execute() {
            try {
                $execValues = [];
                foreach ($this->params as $p) {
                    $execValues[] = $p;
                }
                return $this->pdoStmt->execute($execValues);
            } catch (Exception $e) {
                $this->error = $e->getMessage();
                return false;
            }
        }

        public function get_result() {
            try {
                $rows = $this->pdoStmt->fetchAll(PDO::FETCH_ASSOC);
                return new PDOResultWrapper($rows);
            } catch (Exception $e) {
                $this->error = $e->getMessage();
                return new PDOResultWrapper([]);
            }
        }

        public function close() {
            $this->pdoStmt = null;
            $this->params = [];
            return true;
        }
    }
}

if (!class_exists('PDODatabaseWrapper')) {
    class PDODatabaseWrapper {
        private $pdo;
        public $connect_error = null;
        public $error = '';
        public $insert_id = 0;
        public $affected_rows = 0;

        public function __construct(PDO $pdo) {
            $this->pdo = $pdo;
        }

        public function query($sql) {
            $this->error = '';
            $trimmed = trim($sql);
            
            // Normalize MySQL-specific GROUP BY for title dropdown queries
            if (preg_match('/select\s+DISTINCT\s+\*\s+from\s+schedule\s+GROUP\s+BY\s+title/i', $trimmed)) {
                $trimmed = 'select DISTINCT title from schedule';
            }

            try {
                $isSelect = preg_match('/^(SELECT|SHOW|EXPLAIN|PRAGMA)\s+/i', $trimmed);
                if ($isSelect) {
                    $stmt = $this->pdo->query($trimmed);
                    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
                    return new PDOResultWrapper($rows);
                } else {
                    $affected = $this->pdo->exec($trimmed);
                    $this->affected_rows = ($affected !== false) ? $affected : 0;
                    $this->insert_id = (int)$this->pdo->lastInsertId();
                    return true;
                }
            } catch (Exception $e) {
                $this->error = $e->getMessage();
                error_log("Database query error: " . $this->error . " in SQL: " . $sql);
                return false;
            }
        }

        public function prepare($sql) {
            $this->error = '';
            $trimmed = trim($sql);
            try {
                $pdoStmt = $this->pdo->prepare($trimmed);
                return new PDOStatementWrapper($pdoStmt);
            } catch (Exception $e) {
                $this->error = $e->getMessage();
                error_log("Database prepare error: " . $this->error . " in SQL: " . $sql);
                return false;
            }
        }

        public function real_escape_string($str) {
            $quoted = $this->pdo->quote((string)$str);
            // Remove outer quotes added by PDO::quote
            return substr($quoted, 1, -1);
        }

        public function escape_string($str) {
            return $this->real_escape_string($str);
        }

        public function close() {
            $this->pdo = null;
            return true;
        }
    }
}

// 5. Establish Database Connection
$database = null;

if (!isset($skip_db_connect) || !$skip_db_connect) {
    if ($dbType === 'pgsql') {
    // Supabase / PostgreSQL Connection via PDO
    try {
        $dsn = "pgsql:host={$host};port={$port};dbname={$dbname}";
        if (!empty($sslmode)) {
            $dsn .= ";sslmode={$sslmode}";
        }
        $pdo = new PDO($dsn, $user, $pass, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_TIMEOUT => 10,
        ]);
        $database = new PDODatabaseWrapper($pdo);
    } catch (Exception $e) {
        $database = new stdClass();
        $database->connect_error = $e->getMessage();
        die("Échec de la connexion (Supabase/PostgreSQL) : " . $e->getMessage());
    }
} else {
    // MySQL Connection (fallback for local Docker / standard MySQL)
    if (extension_loaded('mysqli')) {
        $database = @new mysqli($host, $user, $pass, $dbname, (int)$port);
        if ($database->connect_error) {
            die("Échec de la connexion : " . $database->connect_error);
        }
    } else {
        // Use PDO MySQL if mysqli extension is not loaded
        try {
            $dsn = "mysql:host={$host};port={$port};dbname={$dbname};charset=utf8mb4";
            $pdo = new PDO($dsn, $user, $pass, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            ]);
            $database = new PDODatabaseWrapper($pdo);
        } catch (Exception $e) {
            die("Échec de la connexion (MySQL) : " . $e->getMessage());
        }
    }
}
}
?>
