(() => {
  const input = document.getElementById('name-input')
  const button = document.getElementById('greet-btn')
  const output = document.getElementById('output')

  if (!input || !button || !output) return

  async function showGreeting() {
    const name = input.value.trim() || 'بلال علي'

    try {
      button.disabled = true
      output.textContent = 'جاري التحميل...'

      const response = await fetch(`/api/greet?name=${encodeURIComponent(name)}`)
      if (!response.ok) throw new Error('فشل الاتصال بالخادم')

      const { greeting, name: returnedName, time, date } = await response.json()
      output.innerHTML = `
        <div class="result">
          <strong>${greeting}، ${returnedName}!</strong>
          <span>التاريخ: ${date}</span>
          <span>الوقت: ${time}</span>
        </div>
      `
    } catch (error) {
      output.textContent = 'حدث خطأ، جرب مرة أخرى.'
      console.error(error)
    } finally {
      button.disabled = false
      input.focus()
    }
  }

  button.addEventListener('click', showGreeting)
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') showGreeting()
  })
})()