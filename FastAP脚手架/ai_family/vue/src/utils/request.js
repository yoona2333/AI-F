import axios from "axios";
import {ElMessage} from "element-plus";

const request = axios.create({
    baseURL: import.meta.env.VITE_BASE_URL,
    timeout: 60000
})

request.interceptors.request.use(config => {
    if (!(config.data instanceof FormData)) {
        config.headers['Content-Type'] = 'application/json;charset=utf-8'
    }
    return config
}, error => {
    return Promise.reject(error)
});

// 业务异常返回 HTTP 200，错误信息在 Result 的 code / msg 中；
// 接口不存在、请求方法不支持、系统异常返回对应的 HTTP 状态码，响应体同样是 Result。
request.interceptors.response.use(
    response => {
        let res = response.data;
        if (response.config.responseType === 'blob') {
            return res
        }
        if (typeof res === 'string') {
            res = res ? JSON.parse(res) : res
        }
        if (res?.code && res.code !== '200') {
            ElMessage.error(res.msg || '请求失败')
        }
        return res;
    },
    error => {
        const message = error.response?.data?.msg
        if (message) {
            ElMessage.error(message)
        } else if (error.response) {
            ElMessage.error(`请求失败（HTTP ${error.response.status}）`)
        } else {
            ElMessage.error('网络连接失败，请确认后端已启动')
        }
        return Promise.reject(error)
    }
)

export default request
