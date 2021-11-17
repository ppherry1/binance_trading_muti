module.exports = {
    apps: [{
            // 网格策略
            name: 'binance_grid',
            cmd: 'binance_infnet_main.py',
            args: '',
            interpreter: 'python3.7',
            out_file: '../log/grid.log',
            error_file: '../log/grid_error.log',
            log_date_format: 'YYYY-MM-DD HH:mm',
            merge_logs: true,
            max_restarts: 5
    }]
};