<template>
  <section class="panel">
    <h2>练习提交</h2>
    <p>题目：为什么只看训练准确率可能误导学习效果判断？请结合“泛化”或“过拟合”回答。</p>
    <textarea v-model="answer" rows="5"></textarea>
    <button class="btn" @click="$emit('submit', [answer])">提交练习</button>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
defineEmits<{ submit: [answers: string[]] }>()
const answer = ref('只看训练准确率可能忽略过拟合，模型在新数据上的泛化能力可能下降。')
</script>
