import React from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Typography,
    Box,
    Grid,
    Paper,
    useTheme,
    Chip,
    Divider,
    Stack
} from '@mui/material';
import { safetyColors } from '../../theme/AppTheme';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import FingerprintIcon from '@mui/icons-material/Fingerprint';

interface ExceptionAlgorithmDialogProps {
    open: boolean;
    onClose: () => void;
}

const ExceptionAlgorithmDialog: React.FC<ExceptionAlgorithmDialogProps> = ({ open, onClose }) => {
    const theme = useTheme();
    const isDark = theme.palette.mode === 'dark';

    // Visual styles
    const flowBoxStyle = {
        p: 2, 
        border: `1px solid ${theme.palette.divider}`,
        borderRadius: 2,
        textAlign: 'center' as const,
        height: '100%',
        display: 'flex',
        flexDirection: 'column' as const,
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.paper',
        boxShadow: theme.shadows[1]
    };

    const arrowStyle = { 
        fontSize: 32, 
        color: theme.palette.text.disabled, 
        my: 1,
        transform: { xs: 'rotate(90deg)', md: 'none' } 
    };

    return (
        <Dialog 
            open={open} 
            onClose={onClose} 
            maxWidth="lg" 
            fullWidth
            scroll="paper"
        >
            <DialogTitle sx={{ borderBottom: 1, borderColor: 'divider', pb: 2 }}>
                <Typography variant="h5" component="div" fontWeight="bold">
                    異常判定演算法說明 (Algorithm Logic)
                </Typography>
            </DialogTitle>
            
            <DialogContent sx={{ p: 4 }}>
                <Grid container spacing={4}>
                    
                    {/* Section 1: Threshold Determination Flow */}
                    <Grid item xs={12}>
                        <Typography variant="h6" gutterBottom color="primary" fontWeight="bold">
                            1. 閾值判定邏輯 (Threshold Determination)
                        </Typography>
                        <Typography variant="body1" paragraph color="text.secondary">
                            系統如何決定某個位置的合格標準？這是透過多重參數的交叉比對：
                        </Typography>

                        <Grid container spacing={2} alignItems="center" justifyContent="center" sx={{ mt: 1 }}>
                            {/* Step 1: Context */}
                            <Grid item xs={12} md={2}>
                                <Paper sx={flowBoxStyle}>
                                    <Typography variant="subtitle2" color="primary" gutterBottom>1. 上下文 (Context)</Typography>
                                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
                                        <Chip label="Line (TOV1050)" size="small" color="default" />
                                        <Chip label="Direction (UT / DT)" size="small" color="default" />
                                    </Box>
                                    <Typography variant="caption" sx={{ mt: 1, display: 'block' }}>用戶選擇</Typography>
                                </Paper>
                            </Grid>

                            <Grid item xs={12} md={0.5} sx={{ display: 'flex', justifyContent: 'center' }}>
                                <ArrowForwardIcon sx={arrowStyle} />
                            </Grid>

                            {/* Step 2: Location Data */}
                            <Grid item xs={12} md={2.5}>
                                <Paper sx={flowBoxStyle}>
                                    <Typography variant="subtitle2" color="secondary" gutterBottom>2. 定位數據 (Input)</Typography>
                                    <Typography variant="h6" fontWeight="bold">Chainage</Typography>
                                    <Typography variant="caption" color="text.secondary">(e.g., 10500)</Typography>
                                    <Divider sx={{ width: '100%', my: 1 }} />
                                    <Typography variant="body2" fontWeight="bold">Exception Type</Typography>
                                    <Typography variant="caption" color="text.secondary">(e.g., Height)</Typography>
                                </Paper>
                            </Grid>

                            <Grid item xs={12} md={0.5} sx={{ display: 'flex', justifyContent: 'center' }}>
                                <ArrowForwardIcon sx={arrowStyle} />
                            </Grid>

                            {/* Step 3: Metadata Lookup */}
                            <Grid item xs={12} md={3}>
                                <Paper sx={{ ...flowBoxStyle, bgcolor: isDark ? 'rgba(25, 118, 210, 0.08)' : '#F0F7FF', borderColor: 'primary.main' }}>
                                    <Typography variant="subtitle2" color="primary" gutterBottom>3. 屬性映射 (Mapping)</Typography>
                                    <Stack spacing={1} width="100%">
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                                            <Typography variant="caption">Chainage →</Typography>
                                            <Chip label="Class: Mainline" size="small" color="primary" variant="outlined" />
                                        </Box>
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                                            <Typography variant="caption">Chainage →</Typography>
                                            <Chip label="Track Type: Curve" size="small" color="secondary" variant="outlined" />
                                        </Box>
                                    </Stack>
                                </Paper>
                            </Grid>

                            <Grid item xs={12} md={0.5} sx={{ display: 'flex', justifyContent: 'center' }}>
                                <ArrowForwardIcon sx={arrowStyle} />
                            </Grid>

                            {/* Step 4: Output */}
                            <Grid item xs={12} md={2}>
                                <Paper sx={{ ...flowBoxStyle, border: '2px solid', borderColor: 'success.main' }}>
                                    <Typography variant="subtitle2" color="success.main" gutterBottom>4. 輸出閾值</Typography>
                                    <Stack spacing={0.5} alignItems="center">
                                        <Typography variant="caption" fontWeight="bold">L1 Limit</Typography>
                                        <Typography variant="caption" fontWeight="bold">L2 Limit</Typography>
                                        <Typography variant="caption" fontWeight="bold">L3 Limit</Typography>
                                    </Stack>
                                </Paper>
                            </Grid>
                        </Grid>
                    </Grid>

                    <Grid item xs={12}>
                        <Divider />
                    </Grid>

                    {/* Section 2: Severity Levels */}
                    <Grid item xs={12}>
                        <Typography variant="h6" gutterBottom color="primary" fontWeight="bold">
                            2. 嚴重程度分級 (Severity Levels)
                        </Typography>
                        <Grid container spacing={2}>
                            <Grid item xs={12} md={4}>
                                <Paper sx={{ p: 2, borderLeft: `6px solid ${safetyColors.l1}`, height: '100%' }}>
                                    <Typography variant="subtitle1" fontWeight="bold" color="error.main">L1 (Critical)</Typography>
                                    <Typography variant="caption" display="block" gutterBottom>安全極限 (Safety Limit)</Typography>
                                    <Typography variant="body2" sx={{ mt: 1 }}>
                                        超出此範圍代表有即時安全風險。
                                        <br/><strong>行動:</strong> 立即處置 (Immediate Action)。
                                    </Typography>
                                </Paper>
                            </Grid>
                            <Grid item xs={12} md={4}>
                                <Paper sx={{ p: 2, borderLeft: `6px solid ${safetyColors.l2}`, height: '100%' }}>
                                    <Typography variant="subtitle1" fontWeight="bold" sx={{ color: safetyColors.l2 }}>L2 (Warning)</Typography>
                                    <Typography variant="caption" display="block" gutterBottom>維修極限 (Maintenance Limit)</Typography>
                                    <Typography variant="body2" sx={{ mt: 1 }}>
                                        數值劣化但尚未影響行車安全。
                                        <br/><strong>行動:</strong> 列入計畫維修 (Planned Maintenance)。
                                    </Typography>
                                </Paper>
                            </Grid>
                            <Grid item xs={12} md={4}>
                                <Paper sx={{ p: 2, borderLeft: `6px solid ${safetyColors.l3}`, height: '100%' }}>
                                    <Typography variant="subtitle1" fontWeight="bold" sx={{ color: safetyColors.l3 }}>L3 (Info)</Typography>
                                    <Typography variant="caption" display="block" gutterBottom>監控極限 (Monitor Limit)</Typography>
                                    <Typography variant="body2" sx={{ mt: 1 }}>
                                        輕微偏差，作為早期預警。
                                        <br/><strong>行動:</strong> 持續觀察 (Keep Monitoring)。
                                    </Typography>
                                </Paper>
                            </Grid>
                        </Grid>
                    </Grid>

                    <Grid item xs={12}>
                        <Divider />
                    </Grid>

                    {/* Section 3: Key Metrics & History Compare Link */}
                    <Grid item xs={12}>
                        <Typography variant="h6" gutterBottom color="primary" fontWeight="bold">
                            3. 關鍵指標與歷史比對 (Key Metrics)
                        </Typography>
                        <Grid container spacing={3}>
                            <Grid item xs={12} md={6}>
                                <Paper variant="outlined" sx={{ p: 2 }}>
                                    <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
                                        <BarChartIcon color="action" />
                                        <Typography variant="subtitle1" fontWeight="bold">MaxValue (最大值)</Typography>
                                    </Stack>
                                    <Typography variant="body2" color="text.secondary">
                                        在異常區間內，偏離標準最嚴重的數值。
                                    </Typography>
                                    <Typography variant="body2" sx={{ mt: 1, fontWeight: 'medium' }}>
                                        用途：決定該異常的嚴重等級 (L1/L2/L3)。
                                    </Typography>
                                </Paper>
                            </Grid>
                            <Grid item xs={12} md={6}>
                                <Paper variant="outlined" sx={{ p: 2, borderColor: 'secondary.main', bgcolor: isDark ? 'rgba(156, 39, 176, 0.05)' : '#FFF9FF' }}>
                                    <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
                                        <FingerprintIcon color="secondary" />
                                        <Typography variant="subtitle1" fontWeight="bold" color="secondary">MaxLocation (峰值位置)</Typography>
                                    </Stack>
                                    <Typography variant="body2" color="text.secondary">
                                        異常數值達到最大值時的確切里程位置 (Chainage)。
                                    </Typography>
                                    <Box sx={{ mt: 2, p: 1.5, bgcolor: 'background.paper', borderRadius: 1, border: '1px dashed', borderColor: 'secondary.main' }}>
                                        <Typography variant="caption" color="secondary" fontWeight="bold" display="block">
                                            ⚠️ 在歷史比對中的重要性：
                                        </Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            MaxLocation 是異常的「指紋」。即使兩次檢測的異常範圍有重疊，如果 <strong>MaxLocation 發生位移 (Peak Drift)</strong> 超出重疊區，系統將視為不同的問題，避免誤判。
                                        </Typography>
                                    </Box>
                                </Paper>
                            </Grid>
                        </Grid>
                    </Grid>

                </Grid>
            </DialogContent>
            <DialogActions sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
                <Button onClick={onClose} variant="contained">
                    了解 (Understood)
                </Button>
            </DialogActions>
        </Dialog>
    );
};

// Simple Icon Component for visual consistency
const BarChartIcon = (props: any) => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
        <line x1="12" y1="20" x2="12" y2="10" />
        <line x1="18" y1="20" x2="18" y2="4" />
        <line x1="6" y1="20" x2="6" y2="16" />
    </svg>
);

export default ExceptionAlgorithmDialog;
