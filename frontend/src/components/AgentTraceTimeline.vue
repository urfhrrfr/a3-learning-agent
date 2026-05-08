<template>
  <section class="panel">
    <h2>Agent Trace</h2>
    <div v-if="traces.length" class="timeline">
      <div v-for="trace in traces" :key="trace.id" class="timeline-item">
        <div class="split"><b>{{ trace.agent }}</b><span class="status">{{ trace.status }}</span></div>
        <div class="muted">{{ trace.input_summary }}</div>
        <p>{{ trace.output_summary }}</p>
        <div class="chips"><span v-for="ref in trace.source_refs" :key="ref" class="chip">{{ ref }}</span></div>
      </div>
    </div>
    <p v-else class="muted">发起资源生成后，这里会展示每个智能体的输入、输出、来源和状态。</p>
  </section>
</template>

<script setup lang="ts">
import type { AgentTrace } from '../types'
defineProps<{ traces: AgentTrace[] }>()
</script>
