<template>
  <div class="home-hero">
    <div class="scene-container">
      <!-- 主视觉文案 -->
      <div class="hero-text">
        <h1 class="hero-title">
        <span style="color: #545454;">Don't type,</span> 
        <span class="italic font-serif" style="color: #1e1d1d; margin-left: 0.8rem;">just speak</span>
        </h1>
        <p class="hero-subtitle mx-auto">
VoiceFlow Input: speak once, get polished text and meeting notes.</p>
      </div>
      <!-- 动效区域 -->
      <div class="animation-wrapper">
        <!-- 底层 SVG -->
        <svg class="svg-layer layer-base" overflow="visible" preserveAspectRatio="xMidYMid meet" viewBox="0 0 1400 300">
          <defs>
            <path d="M -800,150 C -300,150 50,350 200,350 C 350,350 350,-50 150,-50 C -100,-60 0,300 300,230 C 550,200 550,150 700,150 C 850,180 900,50 1050,50 C 1200,50 1250,250 1450,250 C 1650,250 1750,150 2000,150" id="text-curve"></path>
          </defs>
          <text>
            <textPath href="#text-curve" startOffset="0%">
              <animate attributeName="startOffset" begin="0s" calcMode="linear" dur="20s" from="-50%" repeatCount="indefinite" to="0%"></animate>
              although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project.
            </textPath>
          </text>
        </svg>
        <!-- 顶层 SVG 容器（带剪裁） -->
        <div class="layer-top-container" style="clip-path: polygon(50% -200%, 100% -200%, 100% 300%, 50% 300%);">
          <svg class="svg-layer layer-top" overflow="visible" preserveAspectRatio="xMidYMid meet" viewBox="0 0 1400 300">
            <!-- 黑色背景色带 -->
            <use class="curve-stroke" fill="none" href="#text-curve"></use>
            <!-- 白色文字 -->
            <text>
              <textPath href="#text-curve" startOffset="0%">
                <animate attributeName="startOffset" begin="0s" calcMode="linear" dur="20s" from="-50%" repeatCount="indefinite" to="0%"></animate>
                although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project. although it's probably going to slip. there's been a lot of back and forth and honestly the whole thing's been kind of chaotic, like nobody's really bad. i think they're going to handle the first part of the project.
              </textPath>
            </text>
          </svg>
        </div>
        <!-- 录音按钮 (节点) -->
        <div class="node-button cursor-pointer" style="width: 200px; height: 75px;" @click="$emit('enter-app')">
          <!-- Left cluster -->
          <div class="wave-bar" style="height: 35px; animation-duration: 0.8s; animation-delay: -0.1s;"></div>
          <div class="wave-bar" style="height: 25px; animation-duration: 0.9s; animation-delay: -0.5s;"></div>
          <div class="wave-bar" style="height: 40px; animation-duration: 0.7s; animation-delay: -0.2s;"></div>
          <div class="wave-bar" style="height: 30px; animation-duration: 1.1s; animation-delay: -0.8s;"></div>
          <div class="wave-bar" style="height: 45px; animation-duration: 0.85s; animation-delay: -0.4s;"></div>
          <div class="wave-bar" style="height: 25px; animation-duration: 1.2s; animation-delay: -0.9s;"></div>
          <div class="wave-bar" style="height: 35px; animation-duration: 0.9s; animation-delay: -0.3s;"></div>
          <!-- Middle dots/small bars -->
          <div class="wave-bar" style="height: 10px; animation-duration: 1.0s; animation-delay: -0.6s;"></div>
          <div class="wave-bar" style="height: 8px; animation-duration: 0.75s; animation-delay: -0.1s;"></div>
          <div class="wave-bar" style="height: 12px; animation-duration: 0.85s; animation-delay: -0.7s;"></div>
          <div class="wave-bar" style="height: 8px; animation-duration: 1.1s; animation-delay: -0.2s;"></div>
          <div class="wave-bar" style="height: 10px; animation-duration: 0.9s; animation-delay: -0.5s;"></div>
          <div class="wave-bar" style="height: 8px; animation-duration: 0.8s; animation-delay: -0.8s;"></div>
          <!-- Right cluster -->
          <div class="wave-bar" style="height: 40px; animation-duration: 1.0s; animation-delay: -0.3s;"></div>
          <div class="wave-bar" style="height: 50px; animation-duration: 0.95s; animation-delay: -0.6s;"></div>
          <div class="wave-bar" style="height: 55px; animation-duration: 0.8s; animation-delay: -0.1s;"></div>
          <div class="wave-bar" style="height: 45px; animation-duration: 1.1s; animation-delay: -0.9s;"></div>
          <div class="wave-bar" style="height: 50px; animation-duration: 0.85s; animation-delay: -0.4s;"></div>
        </div>
      </div>
      <!-- 底部设备支持提示 -->
      <div class="absolute bottom-10 text-xs text-gray-400 font-medium tracking-wide">
        AVAILABLE ON MAC, WINDOWS, IPHONE, AND ANDROID
      </div>
      <!-- 右下角浮动按钮 -->
      <div class="absolute bottom-8 left-8 w-12 h-12 bg-[#e6d5ff] rounded-full flex items-center justify-center shadow-lg cursor-pointer floating-icon">
        <svg fill="none" height="20" stroke="black" stroke-width="2" viewBox="0 0 24 24" width="20"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v1a7 7 0 0 1-14 0v-1"></path><line x1="12" x2="12" y1="19" y2="22"></line></svg>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['enter-app'])
</script>

<style scoped>
.home-hero {
    font-family: 'Inter', sans-serif;
    background-color: #F9F8F1;
    overflow: hidden;
    margin: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 9999;
}

.scene-container {
    position: relative;
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.hero-text {
    position: relative; /* 保证层级在最上面 */
    text-align: center;
    z-index: 10;
    margin-bottom: 2rem;
    margin-top: -150px;
}

.hero-title {
    font-size: 5rem;
    font-weight: 500;
    color: #111111 !important; /* 强制颜色，防止被暗黑模式变白 */
    letter-spacing: -0.02em;
    margin-bottom: 1rem;
    
    /* 清除 main.css 里对 h1 全局设置的渐变色 */
    background: none !important;
    -webkit-text-fill-color: initial !important;
    -webkit-background-clip: initial !important;
}

.hero-subtitle {
    font-size: 1.25rem;
    color: #333333 !important; /* 强制颜色，防止被暗黑模式变白 */
    max-width: 500px;
    line-height: 1.5;
}

.animation-wrapper {
    position: absolute;
    bottom: 15%;
    width: 120%;
    height: 300px;
    left: -10%;
    pointer-events: none;
}

.svg-layer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
}

.layer-base {
    z-index: 1;
}
.layer-base text {
    fill: #999;
    font-size: 24px;
    font-weight: 500;
    text-transform: lowercase;
}

.layer-top-container {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 2;
    clip-path: polygon(50% -200%, 100% -200%, 100% 300%, 50% 300%);
}

.layer-top text {
    fill: white;
    font-size: 24px;
    font-weight: 500;
    text-transform: lowercase;
}

.curve-stroke {
    stroke: #1a1a1a;
    stroke-width: 48px;
    stroke-linecap: round;
}

.node-button {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 280px;
    height: 100px;
    background: #F9F8F1;
    border: 4px solid #1a1a1a;
    border-radius: 100px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    z-index: 100;
    animation: breathe 3s ease-in-out infinite alternate;
    pointer-events: auto;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.node-button:hover {
    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
}
.node-button:active {
    transform: translate(-50%, -50%) scale(0.98);
}

@keyframes breathe {
    0% { transform: translate(-50%, -50%) scale(1); }
    100% { transform: translate(-50%, -50%) scale(1.05); }
}

.wave-bar {
    width: 4px;
    background: #1a1a1a;
    border-radius: 4px;
    animation: wave ease-in-out infinite alternate;
}

@keyframes wave {
    0% { transform: scaleY(0.3); }
    100% { transform: scaleY(1); }
}

.floating-icon {
    animation: float 4s ease-in-out infinite alternate;
    transition: transform 0.3s ease;
    pointer-events: auto;
}

.floating-icon:hover {
    transform: scale(1.1);
}

@keyframes float {
    0% { transform: translateY(0); }
    100% { transform: translateY(-10px); }
}

@media (prefers-reduced-motion: reduce) {
    .wave-bar, .node-button, .hero-text, .floating-icon {
        animation: none;
    }
}
</style>
