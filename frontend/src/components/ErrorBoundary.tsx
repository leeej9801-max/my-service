import { Component } from "react";
import type { ReactNode } from "react";

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  override state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  override render() {
    return this.state.failed ? (
      <p role="alert">Something went wrong. Reload the page to try again.</p>
    ) : (
      this.props.children
    );
  }
}
