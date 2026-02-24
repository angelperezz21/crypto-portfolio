---
name: motion-ux
description: >
  Guía de animaciones y micro-interacciones para el proyecto. Usar cuando se
  añadan transiciones de página, animaciones de entrada de componentes, feedback
  visual de acciones, o cualquier movimiento en la UI. El objetivo es que las
  animaciones refuercen la usabilidad, no que sean decorativas.
---

# Motion & UX — Animaciones que aportan, no distraen

## Principio guía
**Las animaciones son feedback, no espectáculo.**
Cada animación debe responder a "¿qué le comunica esto al usuario?",
no "¿se ve bonito?". Si no comunica nada, se quita.

## Librería: Framer Motion
```tsx
import { motion, AnimatePresence } from "framer-motion"
```

## Presets de animación del proyecto (usar siempre estos, no inventar)

```ts
// lib/motion.ts — exportar desde aquí, usar en todos los componentes

export const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit:    { opacity: 0 },
  transition: { duration: 0.15 }
}

export const slideUp = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit:    { opacity: 0, y: -4 },
  transition: { duration: 0.2, ease: "easeOut" }
}

export const scaleIn = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1 },
  exit:    { opacity: 0, scale: 0.96 },
  transition: { duration: 0.15, ease: "easeOut" }
}

// Para listas: cada item entra con delay escalonado
export const stagger = {
  animate: { transition: { staggerChildren: 0.04 } }
}

export const staggerItem = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.2 }
}
```

## Casos de uso y animación correspondiente

### Transición entre páginas
```tsx
// app/layout.tsx o template.tsx
<motion.div key={pathname} {...slideUp}>
  {children}
</motion.div>
```

### Cards del dashboard — entrada al montar
```tsx
<motion.div {...slideUp} className="bg-[#111111] ...">
  <MetricCard ... />
</motion.div>

// Si hay múltiples cards, usar stagger:
<motion.div className="grid grid-cols-4 gap-4" variants={stagger} animate="animate">
  {metrics.map((m, i) => (
    <motion.div key={m.id} variants={staggerItem}>
      <MetricCard {...m} />
    </motion.div>
  ))}
</motion.div>
```

### Número que cambia (contador animado)
```tsx
// Cuando el valor de una métrica se actualiza tras sync, animarlo
import { useSpring, animated } from "@react-spring/web"  // alternativa ligera

function AnimatedNumber({ value }: { value: number }) {
  const { num } = useSpring({ num: value, from: { num: 0 }, config: { tension: 120, friction: 14 } })
  return <animated.span>{num.to(n => formatCurrency(n))}</animated.span>
}
```

### Tooltip / Dropdown — entrada y salida
```tsx
<AnimatePresence>
  {isOpen && (
    <motion.div {...scaleIn}
      className="absolute top-full mt-1 bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg shadow-xl">
      {children}
    </motion.div>
  )}
</AnimatePresence>
```

### Botón de sync — estado de carga
```tsx
// El icono rota mientras sincroniza
<Button onClick={triggerSync} disabled={isSyncing}>
  <motion.div animate={isSyncing ? { rotate: 360 } : { rotate: 0 }}
    transition={isSyncing ? { duration: 1, repeat: Infinity, ease: "linear" } : {}}>
    <RefreshCw className="w-4 h-4" />
  </motion.div>
  {isSyncing ? "Sincronizando..." : "Sincronizar"}
</Button>
```

### Valor positivo/negativo — flash de color al actualizar
```tsx
// Cuando el P&L cambia tras sync, hacer flash verde/rojo brevemente
const [flash, setFlash] = useState(false)
useEffect(() => {
  setFlash(true)
  setTimeout(() => setFlash(false), 600)
}, [value])

<motion.span
  animate={flash ? { backgroundColor: isPositive ? "#10b98133" : "#ef444433" } : { backgroundColor: "transparent" }}
  transition={{ duration: 0.3 }}
  className="tabular-nums rounded px-1">
  {formatCurrency(value)}
</motion.span>
```

### Toast de notificación (sync completado, error)
```tsx
<AnimatePresence>
  {toast && (
    <motion.div
      initial={{ opacity: 0, y: 24, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.95 }}
      className="fixed bottom-6 right-6 bg-[#1c1c1c] border border-[#2a2a2a]
                 rounded-xl p-4 shadow-2xl flex items-center gap-3">
      <CheckCircle className="w-4 h-4 text-emerald-400" />
      <span className="text-sm text-white">{toast.message}</span>
    </motion.div>
  )}
</AnimatePresence>
```

## Lo que NO se anima

- **Cambios de datos en tablas** — demasiado ruido visual
- **El fondo / overlay** — `bg-black/50` aparece instantáneo
- **Elementos fuera del viewport** — `viewport={{ once: true }}` en motion.div
- **Nada con `duration > 0.35s`** — si tarda más, se percibe como lag
- **Transiciones de color en hover** — esas van por CSS `transition-colors`, no Framer

## CSS transitions (para hover/focus — NO usar Framer Motion)
```tsx
// Solo CSS para estados de hover, es más eficiente
className="transition-colors duration-150"    // color
className="transition-all duration-200"       // múltiples propiedades (usar con moderación)
className="transition-opacity duration-150"   // opacidad
```