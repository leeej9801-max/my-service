import { BrowserRouter, Link, Route, Routes } from "react-router";
import { Health } from "@/features/health/Health";

export function App() {
  return (
    <BrowserRouter>
      <main>
        <Routes>
          <Route path="/" element={<Health />} />
          <Route
            path="*"
            element={
              <>
                <h1>Page not found</h1>
                <Link to="/">Home</Link>
              </>
            }
          />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
