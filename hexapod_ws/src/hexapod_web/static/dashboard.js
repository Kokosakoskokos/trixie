// Hexapod Dashboard - ROS2 Web Interface
// Uses roslibjs for WebSocket connection to ROS2

class HexapodDashboard {
    constructor() {
        this.ros = null;
        this.connected = false;
        this.cmdVelPub = null;
        this.gaitPub = null;
        this.aiCommandPub = null;
        this.cameraPub = null;
        
        this.linearSpeed = 0.1;
        this.angularSpeed = 0.5;
        this.currentGait = 'tripod';
        this.aiEnabled = false;
        
        // Camera
        this.cameraStreaming = false;
        this.cameraStreamUrl = null;
        
        this.init();
    }
    
    init() {
        this.connectROS();
        this.setupEventListeners();
        this.updateConnectionStatus();
    }
    
    connectROS() {
        // Connect to rosbridge_server
        this.ros = new ROSLIB.Ros({
            url: 'ws://' + window.location.hostname + ':9090'
        });
        
        this.ros.on('connection', () => {
            console.log('Connected to ROS2');
            this.connected = true;
            this.updateConnectionStatus();
            this.setupPublishers();
            this.setupSubscribers();
            this.log('Connected to robot', 'info');
        });
        
        this.ros.on('error', (error) => {
            console.error('ROS2 connection error:', error);
            this.connected = false;
            this.updateConnectionStatus();
            this.log('Connection error', 'error');
        });
        
        this.ros.on('close', () => {
            console.log('Disconnected from ROS2');
            this.connected = false;
            this.updateConnectionStatus();
            this.log('Disconnected', 'warn');
            
            // Try to reconnect after 3 seconds
            setTimeout(() => this.connectROS(), 3000);
        });
    }
    
    setupPublishers() {
        // cmd_vel publisher
        this.cmdVelPub = new ROSLIB.Topic({
            ros: this.ros,
            name: '/cmd_vel',
            messageType: 'geometry_msgs/Twist'
        });
        
        // gait_type publisher
        this.gaitPub = new ROSLIB.Topic({
            ros: this.ros,
            name: '/gait_type',
            messageType: 'std_msgs/String'
        });
        
        // ai/command publisher
        this.aiCommandPub = new ROSLIB.Topic({
            ros: this.ros,
            name: '/ai/command',
            messageType: 'std_msgs/String'
        });
        
        // camera/command publisher
        this.cameraPub = new ROSLIB.Topic({
            ros: this.ros,
            name: '/camera/command',
            messageType: 'std_msgs/String'
        });
        
        // tracking/command publisher
        this.trackingPub = new ROSLIB.Topic({
            ros: this.ros,
            name: '/tracking/command',
            messageType: 'std_msgs/String'
        });
    }
    
    setupSubscribers() {
        // Ultrasonic sensors
        this.subscribeToTopic('/ultrasonic/front', 'sensor_msgs/Range', (msg) => {
            document.getElementById('dist-front').textContent = msg.range.toFixed(2);
        });
        
        this.subscribeToTopic('/ultrasonic/left', 'sensor_msgs/Range', (msg) => {
            document.getElementById('dist-left').textContent = msg.range.toFixed(2);
        });
        
        this.subscribeToTopic('/ultrasonic/right', 'sensor_msgs/Range', (msg) => {
            document.getElementById('dist-right').textContent = msg.range.toFixed(2);
        });
        
        // IMU
        this.subscribeToTopic('/imu/data', 'sensor_msgs/Imu', (msg) => {
            this.updateIMU(msg.linear_acceleration);
        });
        
        // AI decisions
        this.subscribeToTopic('/ai/decision', 'std_msgs/String', (msg) => {
            try {
                const decision = JSON.parse(msg.data);
                this.logAI(decision);
            } catch (e) {
                this.log('AI: ' + msg.data, 'ai');
            }
        });
        
        // Person tracking status
        this.subscribeToTopic('/tracking/status', 'std_msgs/String', (msg) => {
            this.updateTrackingStatus(msg.data);
        });
    }
    
    subscribeToTopic(topicName, messageType, callback) {
        const topic = new ROSLIB.Topic({
            ros: this.ros,
            name: topicName,
            messageType: messageType
        });
        topic.subscribe(callback);
    }
    
    updateIMU(accel) {
        // Update acceleration bars
        const maxAccel = 20; // m/s^2
        
        const updateBar = (id, value) => {
            const bar = document.getElementById(id);
            const valDisplay = document.getElementById(id + '-val');
            
            if (bar && valDisplay) {
                const percentage = Math.min(100, Math.abs(value) / maxAccel * 50);
                bar.style.height = percentage + '%';
                
                if (value < 0) {
                    bar.classList.add('negative');
                    bar.style.bottom = 'auto';
                    bar.style.top = '50%';
                } else {
                    bar.classList.remove('negative');
                    bar.style.bottom = '50%';
                    bar.style.top = 'auto';
                }
                
                valDisplay.textContent = value.toFixed(2);
            }
        };
        
        updateBar('accel-x', accel.x);
        updateBar('accel-y', accel.y);
        updateBar('accel-z', accel.z);
    }
    
    setupEventListeners() {
        // D-pad controls
        const btnUp = document.getElementById('btn-up');
        const btnDown = document.getElementById('btn-down');
        const btnLeft = document.getElementById('btn-left');
        const btnRight = document.getElementById('btn-right');
        const btnStop = document.getElementById('btn-stop');
        
        // Movement buttons
        btnUp.addEventListener('mousedown', () => this.move(1, 0, 0));
        btnUp.addEventListener('mouseup', () => this.stop());
        btnUp.addEventListener('mouseleave', () => this.stop());
        btnUp.addEventListener('touchstart', (e) => { e.preventDefault(); this.move(1, 0, 0); });
        btnUp.addEventListener('touchend', (e) => { e.preventDefault(); this.stop(); });
        
        btnDown.addEventListener('mousedown', () => this.move(-1, 0, 0));
        btnDown.addEventListener('mouseup', () => this.stop());
        btnDown.addEventListener('mouseleave', () => this.stop());
        btnDown.addEventListener('touchstart', (e) => { e.preventDefault(); this.move(-1, 0, 0); });
        btnDown.addEventListener('touchend', (e) => { e.preventDefault(); this.stop(); });
        
        btnLeft.addEventListener('mousedown', () => this.move(0, 1, 0));
        btnLeft.addEventListener('mouseup', () => this.stop());
        btnLeft.addEventListener('mouseleave', () => this.stop());
        btnLeft.addEventListener('touchstart', (e) => { e.preventDefault(); this.move(0, 1, 0); });
        btnLeft.addEventListener('touchend', (e) => { e.preventDefault(); this.stop(); });
        
        btnRight.addEventListener('mousedown', () => this.move(0, -1, 0));
        btnRight.addEventListener('mouseup', () => this.stop());
        btnRight.addEventListener('mouseleave', () => this.stop());
        btnRight.addEventListener('touchstart', (e) => { e.preventDefault(); this.move(0, -1, 0); });
        btnRight.addEventListener('touchend', (e) => { e.preventDefault(); this.stop(); });
        
        btnStop.addEventListener('click', () => this.stop());
        
        // Speed sliders
        const linearSlider = document.getElementById('linear-speed');
        const angularSlider = document.getElementById('angular-speed');
        
        linearSlider.addEventListener('input', (e) => {
            this.linearSpeed = parseFloat(e.target.value);
            document.getElementById('linear-speed-val').textContent = 
                this.linearSpeed.toFixed(2) + ' m/s';
        });
        
        angularSlider.addEventListener('input', (e) => {
            this.angularSpeed = parseFloat(e.target.value);
            document.getElementById('angular-speed-val').textContent = 
                this.angularSpeed.toFixed(1) + ' rad/s';
        });
        
        // Gait buttons
        document.getElementById('gait-tripod').addEventListener('click', () => {
            this.setGait('tripod');
        });
        
        document.getElementById('gait-wave').addEventListener('click', () => {
            this.setGait('wave');
        });
        
        // Autopilot buttons
        document.getElementById('ai-enable').addEventListener('click', () => {
            this.sendAICommand('autopilot on');
            this.aiEnabled = true;
            this.log('🤖 Autopilot ENABLED - Robot is driving itself', 'info');
            this.updateAutopilotUI(true);
        });
        
        document.getElementById('ai-disable').addEventListener('click', () => {
            this.sendAICommand('manual');
            this.aiEnabled = false;
            this.log('👤 MANUAL mode - You are in control', 'info');
            this.updateAutopilotUI(false);
        });
        
        // Camera controls
        document.getElementById('camera-start').addEventListener('click', () => {
            this.startCamera();
        });
        
        document.getElementById('camera-stop').addEventListener('click', () => {
            this.stopCamera();
        });
        
        document.getElementById('camera-snapshot').addEventListener('click', () => {
            this.takeSnapshot();
        });
        
        // Person tracking controls
        document.getElementById('tracking-start').addEventListener('click', () => {
            this.sendTrackingCommand('start');
            this.log('Person tracking started', 'info');
        });
        
        document.getElementById('tracking-stop').addEventListener('click', () => {
            this.sendTrackingCommand('stop');
            this.log('Person tracking stopped', 'info');
        });
        
        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            if (e.repeat) return;
            
            switch(e.key) {
                case 'ArrowUp': case 'w': case 'W':
                    this.move(1, 0, 0);
                    break;
                case 'ArrowDown': case 's': case 'S':
                    this.move(-1, 0, 0);
                    break;
                case 'ArrowLeft': case 'a': case 'A':
                    this.move(0, 0, 1);
                    break;
                case 'ArrowRight': case 'd': case 'D':
                    this.move(0, 0, -1);
                    break;
                case ' ':
                    this.stop();
                    break;
            }
        });
        
        document.addEventListener('keyup', (e) => {
            switch(e.key) {
                case 'ArrowUp': case 'ArrowDown': case 'w': case 's': case 'W': case 'S':
                case 'ArrowLeft': case 'ArrowRight': case 'a': case 'd': case 'A': case 'D':
                    this.stop();
                    break;
            }
        });
    }
    
    move(forward, left, turn) {
        if (!this.connected || this.aiEnabled) return;
        
        const twist = new ROSLIB.Message({
            linear: {
                x: forward * this.linearSpeed,
                y: left * this.linearSpeed,
                z: 0
            },
            angular: {
                x: 0,
                y: 0,
                z: turn * this.angularSpeed
            }
        });
        
        this.cmdVelPub.publish(twist);
    }
    
    stop() {
        if (!this.connected) return;
        
        const twist = new ROSLIB.Message({
            linear: { x: 0, y: 0, z: 0 },
            angular: { x: 0, y: 0, z: 0 }
        });
        
        this.cmdVelPub.publish(twist);
    }
    
    setGait(gaitType) {
        if (!this.connected) return;
        
        const msg = new ROSLIB.Message({
            data: gaitType
        });
        
        this.gaitPub.publish(msg);
        this.currentGait = gaitType;
        
        // Update UI
        document.getElementById('gait-tripod').classList.toggle('active', gaitType === 'tripod');
        document.getElementById('gait-wave').classList.toggle('active', gaitType === 'wave');
        
        this.log('Gait changed to ' + gaitType, 'info');
    }
    
    sendAICommand(command) {
        if (!this.connected) return;
        
        const msg = new ROSLIB.Message({
            data: command
        });
        
        this.aiCommandPub.publish(msg);
    }
    
    updateConnectionStatus() {
        const statusEl = document.getElementById('conn-status');
        const buttons = document.querySelectorAll('.d-btn');
        
        if (this.connected) {
            statusEl.textContent = 'Connected';
            statusEl.classList.remove('disconnected');
            statusEl.classList.add('connected');
            
            buttons.forEach(btn => btn.disabled = false);
        } else {
            statusEl.textContent = 'Disconnected';
            statusEl.classList.remove('connected');
            statusEl.classList.add('disconnected');
            
            buttons.forEach(btn => btn.disabled = true);
        }
    }
    
    log(message, type = 'info') {
        const logsContainer = document.getElementById('system-logs');
        const time = new Date().toLocaleTimeString();
        
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = `<span class="log-time">${time}</span> <span class="log-${type}">${message}</span>`;
        
        logsContainer.appendChild(entry);
        logsContainer.scrollTop = logsContainer.scrollHeight;
        
        // Keep only last 50 entries
        while (logsContainer.children.length > 50) {
            logsContainer.removeChild(logsContainer.firstChild);
        }
    }
    
    logAI(decision) {
        const logsContainer = document.getElementById('ai-logs');
        const time = new Date().toLocaleTimeString();
        
        const reasoning = decision.reasoning || 'No reasoning';
        const action = decision.action || 'unknown';
        
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = `<span class="log-time">${time}</span> <span class="log-ai">[${action}] ${reasoning}</span>`;
        
        logsContainer.appendChild(entry);
        logsContainer.scrollTop = logsContainer.scrollHeight;
        
        // Keep only last 20 entries
        while (logsContainer.children.length > 20) {
            logsContainer.removeChild(logsContainer.firstChild);
        }
    }
    
    // Camera methods
    startCamera() {
        // Camera stream is on port 8081 (camera driver)
        this.cameraStreamUrl = `http://${window.location.hostname}:8081/stream.mjpg`;
        
        const img = document.getElementById('camera-feed');
        img.src = this.cameraStreamUrl;
        
        this.cameraStreaming = true;
        this.updateCameraStatus(true);
        this.log('Camera started', 'info');
        
        // Handle load error
        img.onerror = () => {
            this.cameraStreaming = false;
            this.updateCameraStatus(false);
            this.log('Camera stream failed', 'error');
        };
        
        // Handle successful load
        img.onload = () => {
            this.updateCameraStatus(true);
        };
    }
    
    stopCamera() {
        const img = document.getElementById('camera-feed');
        img.src = '';
        
        this.cameraStreaming = false;
        this.updateCameraStatus(false);
        this.log('Camera stopped', 'info');
    }
    
    updateCameraStatus(online) {
        const indicator = document.getElementById('camera-status-indicator');
        const text = document.getElementById('camera-status-text');
        
        if (online) {
            indicator.classList.remove('offline');
            indicator.classList.add('online');
            text.textContent = 'Live';
        } else {
            indicator.classList.remove('online');
            indicator.classList.add('offline');
            text.textContent = 'Offline';
        }
    }
    
    takeSnapshot() {
        if (!this.cameraStreaming) {
            this.log('Camera not streaming', 'warn');
            return;
        }
        
        const img = document.getElementById('camera-feed');
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth || 640;
        canvas.height = img.naturalHeight || 480;
        
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        
        // Download snapshot
        const link = document.createElement('a');
        link.download = `hexapod_snapshot_${Date.now()}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
        
        this.log('Snapshot saved', 'info');
    }
    
    sendTrackingCommand(command) {
        if (!this.connected) return;
        
        const msg = new ROSLIB.Message({
            data: command
        });
        
        this.trackingPub.publish(msg);
    }
    
    updateTrackingStatus(status) {
        const statusEl = document.getElementById('tracking-status');
        
        if (status.startsWith('tracking:')) {
            const coords = status.split(':')[1];
            statusEl.textContent = `Status: Tracking person at ${coords}`;
            statusEl.style.color = '#00ff00';
        } else if (status === 'lost') {
            statusEl.textContent = 'Status: Person lost';
            statusEl.style.color = '#ff0000';
        } else {
            try {
                const data = JSON.parse(status);
                if (data.status === 'started') {
                    statusEl.textContent = `Status: Sequence started (${data.segments} segments)`;
                } else if (data.status === 'complete') {
                    statusEl.textContent = 'Status: Sequence complete';
                }
            } catch (e) {
                statusEl.textContent = `Status: ${status}`;
            }
        }
    }
    
    updateAutopilotUI(enabled) {
        const autoBtn = document.getElementById('ai-enable');
        const manualBtn = document.getElementById('ai-disable');
        
        if (enabled) {
            autoBtn.classList.add('active');
            manualBtn.classList.remove('active');
            autoBtn.innerHTML = '🟢 Auto ON';
            manualBtn.innerHTML = 'Manual';
        } else {
            autoBtn.classList.remove('active');
            manualBtn.classList.add('active');
            autoBtn.innerHTML = 'Auto ON';
            manualBtn.innerHTML = '🔴 Manual';
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new HexapodDashboard();
});
