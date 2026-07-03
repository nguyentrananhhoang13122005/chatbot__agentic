export function Footer() {
  return (
    <footer className="border-t border-border/40 bg-background/95 mt-auto">
      <div className="container mx-auto max-w-screen-2xl flex flex-col items-center justify-between gap-4 py-8 md:h-20 md:flex-row md:py-0 px-4">
        <p className="text-center text-sm leading-loose text-muted-foreground md:text-left">
          &copy; {new Date().getFullYear()} UniSearch AI. Hệ thống tư vấn tuyển sinh thông minh.
        </p>
      </div>
    </footer>
  );
}
