import { Hono } from 'hono'
import { renderer } from './renderer'

const app = new Hono()

app.use(renderer)

app.get('/', (c) => {
  return c.render(
    <main class="container">
      <h1>👋 مرحباً</h1>
      <section class="card">
        <label for="name-input">ادخل اسمك (اضغط Enter لاستخدام 'بلال علي')</label>
        <input
          id="name-input"
          type="text"
          placeholder="اسمك"
          aria-label="ادخل اسمك"
          autocomplete="name"
        />
        <button id="greet-btn" type="button">عرض التحية</button>
        <output id="output" class="output" aria-live="polite"></output>
      </section>
      <script src="/static/app.js"></script>
    </main>
  )
})

app.get('/api/greet', (c) => {
  const name = c.req.query('name')?.trim() || 'بلال علي'
  const now = new Date()
  const hour = now.getHours()
  const greeting = getGreeting(hour)
  const timeStr = formatDateTime(now)

  return c.json({
    name,
    greeting,
    time: timeStr.time,
    date: timeStr.date,
  })
})

export default app

function getGreeting(hour: number): string {
  if (hour >= 5 && hour < 12) return 'صباح الخير'
  if (hour >= 12 && hour < 17) return 'مساء الخير'
  if (hour >= 17 && hour < 21) return 'مساء النور'
  return 'مساء الخير وتصبح على خير'
}

function formatDateTime(date: Date): { time: string; date: string } {
  const pad = (n: number) => n.toString().padStart(2, '0')
  return {
    time: `${pad(date.getHours())}:${pad(date.getMinutes())}`,
    date: `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
  }
}