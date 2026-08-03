import { Component, type ErrorInfo, type ReactNode } from 'react'

/** The one class component in the app: React still has no hook equivalent of
 * `componentDidCatch`.
 *
 * It wraps the feature slot rather than the whole app on purpose — one feature
 * throwing should cost that feature, not the navigation the user needs to get
 * away from it. */

interface Props {
  children: ReactNode
  /** Changing this resets the boundary — routes.tsx passes the feature id, so
   * navigating away from a crashed feature clears the error. */
  resetKey?: string
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidUpdate(prev: Props) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null })
    }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Replace with your error reporter. Keep the component stack: without it
    // you get a message and no idea which subtree produced it.
    console.error('Feature crashed', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children

    return (
      <div role="alert" className="mx-auto max-w-lg p-8 text-center">
        <h2 className="text-lg font-semibold">This section failed to load</h2>
        <p className="text-muted-foreground mt-2 text-sm">
          The rest of the app still works. Try again, or pick another section.
        </p>
        <p className="text-muted-foreground mt-4 font-mono text-xs break-words">
          {this.state.error.message}
        </p>
        <button
          type="button"
          onClick={() => this.setState({ error: null })}
          className="bg-primary text-primary-foreground mt-6 rounded-md px-4 py-2 text-sm font-medium"
        >
          Try again
        </button>
      </div>
    )
  }
}
